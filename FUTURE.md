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
and that stopped being true several releases ago.** The editor-only files —
every `skribl/static/editor_*.js` — were carved out
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
target is zero. The player's CSS is under `CSS_TARGET` since v315, by serving it
comment-stripped as the JavaScript already was; any further cut is
`harness/tools/cssgraph.py`'s classifier rather than a carve.

The v132 split was attempted and reverted (see `docs/REFACTOR-v132.md`) because
a regex call graph misclassified functions the player needs. **This section used
to say "use an AST; `node` is available" — that was tried and DISPROVED.**
`harness/tools/refgraph.js` fails its own superset gate and would move all four
of the functions the v132 attempt got wrong; the v132 failure was load order,
not classification. Do not spend the day rediscovering that.

### The two editors duplicate their controllers

`app.js` (with the `editor_*.js` carves) and `flip.js` both drive the *same*
shared partials — `_skribl_draw_drawer.html`, `_skribl_music_drawer.html`,
`_skribl_image_drawer.html`. Every fix to code that exists twice must be made
twice, by someone who remembers there are two. Most of this project's
recurring bugs are that sentence playing out.

**This paragraph used to name the wrong code, and an outside audit quoted it.**
Until v312 it listed the eyedropper, recent colours, smoothing, photo
adjustments and music trimming as the duplicated controllers. By then every one
of those rules lived once, in `lib/eyedropper.js`, `lib/recentcolors.js`,
`lib/smoothing.js`, `lib/photofit.js` and `lib/looptrim.js`, and both editors
called them. The v312 audit filed the old list as a High finding and withdrew
it on reading the source. The problem was real and the list was stale: nobody
had measured what was still written twice, so the paragraph kept describing the
last time somebody looked.

**Measure it, do not remember it:** `python3 harness/tools/editordup.py`. It
pairs every named function in Pad with the function of the same name in Flip
and compares the bodies token by token. Its header says what it cannot see,
and why every total it prints is a lower bound. On the tree after v312, most of
the same-named pairs of 100 tokens or more were copies, and most of the copies
were 0.85–1.00 similar. They cluster like this, largest
first (sizes are the tool's to print, not this paragraph's):

    music drawer: trim handles, waveform and loop detail, zoom window,
      loop preview, nudges
    canvas zoom / pan / pinch (initCanvasZoom alone is the largest single
      copy in either editor)
    MP4 export (exportViaWebCodecsMp4)
    draw drawer and tool wiring: paint target, grid density, shape
      knobs, colour sampling
    drawer plumbing: pending-media cards, slider nudgers
    stroke painter, draft save

Two of those are not what a reader of either file would guess. Pad's copy of
the music drawer's loop-detail pan (`dragZoomPan`, gone with the loop detail in
step 2) lived in `editor_photo.js`, not `editor_music.js`. The canvas zoom and
pinch copies are also where the two editors' event families met (Pad bound
mouse and touch, Flip Pointer Events).
Pad's canvas moved onto Pointer Events in v315 (SK312-002) with the pinch left
on touch events as Flip's is.

**THE LIST ABOVE IS THE v312 MEASUREMENT, AND v315 CLOSED MOST OF IT.** Each
of these is now one copy, in a module both editors call: the magnifier and
pinch (`lib/canvaszoom.js`), the music trim drags (`lib/dragtrack.js`), the
loop view and the waveform strip (one module then; since step 2 the music
timeline, `lib/musictimeline.js`), the re-add cards (`lib/pendingcards.js`),
the paint target and drawer pills
(`lib/painttarget.js`), grid density (`lib/gridoverlay.js`), the live loop
engine (`lib/audioloop.js`, which the player shares) and the MP4 encoder
(`lib/mp4export.js`). Three of those merges found a bug that one editor had and
the other did not -- the reason this section exists -- and each is pinned on
both routes. What `harness/tools/editordup.py` still pairs is mostly small, or
differs on purpose: the two editors draw different things (a stroke timeline
against pages), and a shared function that had to know both would be worse than
two short ones.

The v142–v174 work moved eight modules into `static/lib/` (`canvassizes`,
`posted`, `postedui`, `report`, `segslider`, `tooltip`, `hints`, `helpsearch`),
and later releases moved the rest named above. A small same-named pair is often
legitimate glue around a shared module; the tool's `--min-tokens` floor exists
so that glue is not counted as debt. **Resume only for a named cost** -- a bug
fixed in one copy and not the other is the signal -- not to move the number.

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

*(v304: the first step toward C was taken, deliberately small. `/gallery`
lists every Skribl whose author ticked "Show in the public gallery" on the
post sheet — opt-in, default unlisted, nothing recommended; its Hot tab sorts by recent plays. It
is the listing a host feed already reads, rendered by Skribl itself. What it
is not: an account, a follow, a like. Those are still C, and still backed into.)*

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
   H/V — `verify_select.py`. Lasso specifically was not built:
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
   shift-click, or a page's ⋯ → Select through here, to select a run, and Copy / Delete / ×hold /
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
- A recommendation engine. The gallery's Hot tab (v304) is a sort by counted
  plays in the last seven days, at the owner's word; New stays the default,
  and nothing is recommended to anyone.
- ~~Multi-take.~~ **SHIPPED** — a take ends, the canvas locks, "+ Add take"
  appends another and the replay plays them back to back (START-HERE, "the
  canvas lock after a take is deliberate").

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

## 6c. Motion Smear, aimed rather than applied (owner, v295) — BUILT

STATUS. Built: Smear aims itself at what moved and draws what held still once,
and a Select narrows it to the parts you pick (`tweenAimFromSelection`). Pairing
is by shape now (`tweenMatch`), not by stroke-group index as written below. The
reasoning is kept as it was argued.

THE FINDING THAT PRODUCED THIS. The smear looks good when ONE PART of a drawing
moves and the rest holds still -- a swinging arm, a turning head. It reads as a
grey blob when the WHOLE figure travels, because nothing stays solid and the eye
has no anchor. Rendered side by side, same code and same settings, the two cases
are not close. Every bad example produced during the v295 work was the second
case, which is why the effect looked worse than it is.

SELECT THE PART THAT MOVES. The owner's proposal, and it fits the code almost
exactly as it stands: `lib/selection.js` selects BY STROKE GROUP, never by
individual point, and `buildTween` pairs BY STROKE GROUP index. Same unit. A
selection is already the argument the smear wants, with no new bookkeeping and
nothing new in the payload.

  * Sample only the selected runs across the motion; draw every other run once.
  * Measured on a four-stroke figure: 6,912 points against 1,241, 5.6x lighter.
    The ratio GROWS with the drawing, because a real page has far more strokes
    holding still than moving -- which also moves the "too heavy for a motion
    smear" refusal a long way out.
  * The bad case becomes unreachable. You cannot select everything and mean it.

Open questions, none blocking: what a smear with NO selection should do (keep
today's whole-page behaviour is the obvious answer); which page the unselected
strokes should be drawn from when they are not identical on both (page A, and
say so in Help); and whether the trail should FADE along the motion rather than
using flat alpha for every sample, which is one line in the sample loop and
visibly better where the pose lands.

## 6d. Layers (owner, v295, unexplored)

Raised alongside the selection idea and not yet thought through. Worth noting
that Skribl has deliberately had no layer concept: a page is a flat list of
points, which is what makes replay, export, the player and the draft format
simple enough to have stayed stable across three hundred versions. A layer is a
schema change every reader of the format would have to honour -- the same trap
the `pressure` note in flip.js and the blur note in verify_tween both record.
So: possible, and expensive in a way that is not obvious from the UI side. If
the motivation is "smear this part and not that part", the selection above buys
most of it for none of the cost.

## 6e. The filmstrip reorders when you meant to scroll (owner, v295, from a phone)

**CLOSED — kept for the reasoning.** `flip.js` now arms a reorder only after a
hold, raised the slop to `STRIP_JITTER`, and abandons the reorder if the strip's
own scrollLeft moved: both suggestions below, plus the hold. `verify_pages.py`
pins it ("scrolling the strip does not reorder a page", and the flick case).

REPORTED: the page thumbnails are hard to tap to switch pages, and they move too
easily -- scrolling the strip drags a page out of order.

DIAGNOSED, flip.js: a reorder begins after SIX PIXELS of horizontal movement
(`if(!_pdrag.moved && Math.abs(dx)<6) return;`) with no time gate. The strip
SCROLLS HORIZONTALLY, so the scroll gesture and the reorder gesture are the same
gesture, separated by 6px. On a phone that is nothing, and a scroll flick is a
reorder. It also explains the other half of the report: a tap that drifts
slightly sets `_pdragSuppressClick`, so the page never changes.

THE OWNER'S FIX -- hold longer before it moves -- is the right shape, and it
collides with something: those tiles already use a 450 ms hold for the SPAN
SWEEP (hold still, then sweep to select a range), so long-press is taken.
Rehoming that gesture is the real decision.

Two changes that need no gesture redesign and should be tried first:

  * Raise the slop. Six pixels is below every platform's touch slop; iOS uses
    about ten and a filmstrip wants more, not less.
  * Let the scroll win. If the strip's own scrollLeft moved during the gesture,
    the finger was scrolling -- abandon the reorder rather than competing with
    it. This is the discriminator the current code lacks entirely, and unlike a
    threshold it cannot be beaten by a longer drag.

## 6f. Smudge cannot carry ink further than its own brush (measured, v301)

The owner reported that Smudge "feels weird" on ordinary ink as well as on a
Motion Smear. The Motion Smear half was a one-line alpha defect and is fixed.
This half is not a defect and not a constant. It is the mechanism's ceiling,
and it is now measured rather than suspected.

**A drag pulls ink a bounded distance and then stops, however far you drag.**
Same fixture, an O, dragged straight down off the top; depth is how far the ink
actually moved:

    brush  radius |  drag 10    20    40    70   120   200
        3      18 |    20.8  20.8  20.8  20.8  20.8  20.8
        7      42 |    20.8  20.8  27.1  31.7  31.7  31.7
       14      84 |    20.8  20.8  33.3  52.8  69.0  70.2
       28     168 |    20.8  20.8  35.3  60.1  96.5 135.9

At the default brush you can drag 200px and move the ink 31.7. Everything past
roughly the first 40px of the gesture does nothing. That is what reads as
"vector liquify, not pigment": a real smudge comes with your finger, and this
one pinches a notch and lets go.

**The mechanism.** A point moves 0.92 of each delta, so it always lags; lagging
puts it further from the brush centre; `SMUDGE_SHARP` 2.2 makes the weight
collapse with that distance; once the lag reaches the radius the point gets zero
and is abandoned. No strength below 1 avoids it, because the lag accumulates,
and 1 exactly is the spike `LIQUIFY_STRENGTH` documents.

**TWO THINGS THAT LOOK LIKE THE ANSWER AND ARE NOT.** Both were tried here.

*Lower the strength.* The hypothesis was that 0.92 reproduces the convergence
`LIQUIFY_STRENGTH`'s comment measured -- "three parallel lines, all three
converged to one vertex". It does not. On that exact fixture the three lines
pull 57.9 / 9.2 / 0 px and never converge, and the leading ink keeps 58% of a
100px gesture rather than riding it. The sharper falloff already prevents the
documented failure. Tuning the number down only shortens the carry further.

*Release by pigment spent rather than by distance* -- give a point already held
this gesture a floor weight of `1 - acc`, so it lets go when its ink is used up
instead of when it drifts out of the brush. It doubles the carry (31.7 -> 58 at
the default brush) and **looks worse**: the whole held band moves as a rigid
slab, so the V notch becomes a flat-bottomed trough with two horns. Rendered
side by side, the shipped V is the better drawing. Rejected on the picture.

**THE RASTER PROTOTYPE WAS BUILT, AND THE ANSWER IS NO.** The outside review
asked for an image-space smudge on a scratch raster, to learn whether the
ceiling is the mechanism or the tuning. It exists, it works, and it loses.

Five versions were needed before the compositing was even correct, and each
failure is worth recording because a future attempt will otherwise rediscover
them in the same order:

1. *Stamping once per pointer sample.* An 84px tile stamped 90 times eats a
   hole in the line it is dragging. Brushes stamp at a fraction of their own
   diameter.
2. *Coarse spacing to fix that.* Corduroy: every stamp shows as a ridge.
3. *Smudging over an opaque white fill.* Every tile carries ~95% background, so
   every stamp BLEACHES the line. No parameter avoids it. The layer has to be
   transparent -- which Skribl already does for a frame (`frameCv`).
4. *source-over on a transparent layer.* Only ever adds, so two dozen stamps
   per brush-width composite to solid black whatever the strength.
5. *Lerp on lay-down but not on pick-up.* The carry never dilutes crossing bare
   canvas, so the streak comes out one density all the way down -- no taper.
   Depletion is the taper.

With all five fixed the compositing is right, and the output is still a soft
grey band. **Every raster variant replaces a crisp line with mush, and the
shipped V -- the one the owner does not like -- is the sharper, more legible
drawing of the two.** A better-tuned raster smudge than this one certainly
exists; what this establishes is that it is not cheap, and that the thing it
buys is not obviously worth having on a drawing whose whole look is a clean
stroke.

**And the decisive argument does not depend on the prototype's quality at all.
A FRAME IS STROKES.** Smudging to pixels means the page stops being strokes,
and strokes are what Pad replays, what the player draws, what export reads and
what the `.skribl` format stores. Raster smudge is not a rendering change, it
is a format change, and it would cost the one property that makes Skribl
unusual -- that the artefact is a process rather than a picture. That is the
same limit `lib/brushfield.js` already states about blur, and it is the reason
to stop here rather than tune further.

**So the carry ceiling stands as a known, measured limitation.** If it is ever
worth attacking, attack it in vector -- something that keeps strokes as strokes
and beats the shipped V on a side-by-side. Rasterising the page is not the way
past it.

**And do not fix this by making the notch deeper.** Nothing above says the
current output is ugly; it says the tool ignores most of a long gesture. If a
prototype cannot beat the shipped V on a side-by-side, the right answer is to
leave the mechanism alone and say in the UI what it does.

## 6g. The crochet stitch on a Motion Smear (measured, v301)

The owner looked closely at a smear and asked what the pattern was. It is not a
texture: **it is the samples themselves.** A smear is N translucent copies of
the drawing laid along the travel; a closed shape's copies cross their
neighbours, and near the top and bottom of a loop they cross at a shallow angle
and leave a brighter node. Regular spacing, regular nodes, visible moiré.

**THE SAMPLE COUNT IS BRUSH-BLIND, AND THAT IS THE CAUSE.** The planner picks
`min(TWEEN_SAMPLES, what fits the point cap, what fits the group cap)` and
nothing in it knows how wide the brush is. Measured on one drawing at one
travel, the planner chose **27 positions at every brush from 2px to 48px** --
gap always 8.5px. What changes is only whether the brush can bridge it:

    brush   gap/brush   ripple
      2 px      4.25x    28.8%
      3 px      2.83x    29.1%
      7 px      1.21x    13.1%
     20 px      0.42x     8.1%
     48 px      0.18x     1.7%

(Ripple is the tone wobble along the travel after the smooth part is subtracted,
calibrated first against cases already known: 53% at 16 samples, 7.4% at 108.)

**The trail already solved this and the samples never inherited it.**
`SMEAR_TRAIL_OVERLAP` spaces trail ghosts at 0.7 of a brush width, and the
comment beside it tells the owner's own story -- a 3px line travelling 220px,
six ghosts 18px apart, "the page reads as six separate lines". Same failure,
other population.

**THREE FIXES WERE TRIED. ALL THREE ARE REJECTED, AND THE REASONS DIFFER.**

*Sample denser.* Works: 26 -> 120 samples takes the ripple 32.3% -> 5.7%, and
the per-frame budget allows it (39% of the 20,000-point cap). **It does not
scale to a document.** `MAX_TOTAL_POINTS` is 200,000 for the whole Skribl, a
smeared page costs ~1,755 points where a hand-drawn one costs ~65, and so:

    samples      pts/page    smeared pages that fit    100 pages =
      26 (now)      1,755                       113     88% of cap
         120        7,865                        25    393% -- refused

A hundred-slide flipbook of smears is already at 88% of the budget as it
ships. Denser sampling caps it at 25.

*Jitter the sample positions* -- free, breaks the regularity. Measured worse at
every brush width (32.3% -> 36.9% at 2px) and worse to look at: a regular
lattice becomes uneven clumping, which reads as a mistake rather than a texture.

*Trade detail for samples* -- the trail's own trick (`SMEAR_TRAIL_COARSE`: a
ghost carries a quarter of the pose's points). At a flat point total (1,755 ->
1,785) the ripple collapses 32.3% -> 5.8%. It looked like the answer. Rendered,
the O is a visible **polygon**; at 8 points per pose it is a hexagon.

**AND THE INSTRUMENT COULD NOT SEE THAT, WHICH IS THE PART TO REMEMBER.** The
ripple measure subtracts a moving average, so it reads high-frequency wobble.
Faceting is a SMOOTH low-frequency error -- exactly what the subtraction
removes. The number said "fixed" while the drawing got worse. Any future
attempt here needs a shape-fidelity measure beside the ripple one, or it will
be fooled the same way.

So the stitch stands as a **known limit with a price nobody wants to pay**,
not an oversight with a patch behind it. The fix that works does not scale and
the fixes that scale do not work. Do not spend more here without a genuinely
new idea, and whatever it is, judge it on a picture.

**THE ALONG-MOTION ENGINE WAS BUILT AND IT LOSES (v302).** The idea: the
ghosts are drawn ACROSS the motion -- N copies of the whole shape at N instants
-- and photographic blur is streaks ALONG it, so give each source point one
streak from where it starts to where the pose stands, as a single path at a
single alpha, with the falloff coming from nested streaks of decreasing length.
It is cheaper per page and it cannot ripple, because every run is uniform.

Judged on pictures, on two drawings:

  - AN OPEN STROKE, which is the case the effect is named for. The SHIPPED
    engine already looks right: a bright leading edge and a soft trailing haze,
    366 points, no pattern of any kind. Along-motion at 450 points is visibly
    worse -- hatching in the trail and a harder edge. The shipped one wins and
    it is not close.
  - THE RING. Along-motion at 550 points is a venetian blind. At 1,100 it
    smooths out and reads as a solid grey can. Even spacing by arc length
    instead of by angle did not save it.

So the topology change does not escape the trade, it ROTATES it: the artefact
moves from ribbing across the motion to combing along it, and hiding it costs
the same density 6g already measured. Same curve, ninety degrees round.

AND THE MORE USEFUL FINDING IS WHAT THE OPEN STROKE SAYS. Motion Smear is good
at what it was named for. The tube is specific to CLOSED shapes, where every
ghost contributes its far side as well as its near one -- a ring swept along
its axis genuinely fills a tube, and twenty-two outlines of it is a wireframe.
That is geometry, not sampling, and no amount of tuning the sample count
addresses it. If this is ever attacked again, the target is "a closed shape's
ghosts should contribute a silhouette, not an outline", and that is a different
and much harder problem than the one 6g describes.

Opacity was measured at the same time and confirmed what was expected: the
shipped page at 50% shows the SAME moire, dimmer. The ghost-to-gap ratio is
what makes the pattern and scaling every ghost together does not change it. A
control is still worth having -- artists want it -- but it is a control, not a
fix, and must not be sold as one.

**DO NOT CONFUSE THIS WITH THE MESH A SMUDGE USED TO LEAVE (fixed, v302).**
They look alike and they are not the same thing. The stitch above is in the
smear itself, it is the sample count, and it is still there. The mesh appeared
only after a field tool touched a generated page: smudge writes per-point
colour and size, so `uniformRun` stopped giving the ghost a single path, the
per-segment walk took over, and translucent round caps compound where they
meet. A run written at alpha 0.0314 painted 11.2 between vertices and 15.1 at
them, against the 8 a single path gives -- a 35% ripple at the ghost's own
point spacing. `uniformAlpha` and the wet-layer route closed it on both
surfaces. If a stitch-like pattern is ever reported again, the first question
is whether a field tool touched the page: one of these is a design limit and
the other was a renderer bug.

## 6h. Nothing tells you the document budget until you post (v301) — BUILT

Found while measuring 6g, and it is the more actionable of the two.

`MAX_TOTAL_POINTS` is 200,000 across a whole Skribl. **Nothing client-side
tracks it.** The smear planner budgets per FRAME -- `TWEEN_POINT_CAP` 14,000,
`TWEEN_GROUP_CAP` 4,500 -- and no code anywhere sums the document. The limit is
enforced only by the server, at POST.

It is not a silent failure: the server answers "Too many points overall (limit
200000)" and `showShareError` puts it on screen, and the drawing is safe
locally. But it arrives **at the end of the work**, and it names the limit
rather than what is consuming it. A generated page costs roughly **27x a
hand-drawn one** (~1,755 points against ~65 on the same drawing), so the real
budget is "how many smears", and nothing says so until it is spent.

**Done in v301.** `lib/pointbudget.js` owns the client's copy of the cap and
sums the document; Flip checks it *before* Motion Smear and In-between run,
declines with a chip naming the percentage spent and how much of it is
generated, and `shareSkribl` pre-flights the same total instead of letting the
POST discover it. The module is absent-safe on purpose -- if the script fails
to load, `budgetAllows` returns true, because a missing file must not take the
buttons away. The wall at the end is now a number you can watch.

The budget is the DOCUMENT's, so it is summed per document and not per frame:
the per-frame caps (`TWEEN_POINT_CAP`, `TWEEN_GROUP_CAP`) still do their own
job and neither one can see this one.

**AND THE OTHER CEILING WAS THE ONE THAT BOUND FIRST (closed in v302).** Found
while measuring this one. `MAX_FRAMES` is 200, it was enforced only at POST, and
a Motion Smear costs **two** pages -- the pose you draw and the page it
generates -- so 200 arrives at about **99 smears**. Measured across drawing
weights, only a very dense drawing reaches the point budget before the page one:

    pose weight   cost per smear   smears to the point chip   pages by then
    ~64 pts             272                ~735                   1,470
    ~160                680                ~293                     586
    ~400              1,700                ~117                     234
    ~640              2,720                 ~73                     146

On a ring pair the document passed 201 pages at 84,160 points -- **42% of the
point budget** -- saying "Motion smear added" each time, and went on to 261.
So the guard shipped in v301 was watching the ceiling that arrives second.

Both doors are guarded now: `budgetAllows` for the generative buttons and
`addFrame` for Duplicate and Blank, plus the post pre-flight. The message names
PAGES rather than size, because the remedies differ -- over on points you delete
a GENERATED page and free 27 drawings' worth, over on pages any page will do.

**Do not "fix" it by raising MAX_TOTAL_POINTS.** The cap exists to stop a
payload that pins a phone, and the comment above it in `validation.py` says so.
The problem is that the client spends a budget it cannot see.

## 6i. Blooby's card as a Flip: loop a stretch of pages, and a page that stays underneath (owner, after v319) — BUILT

**BUILT — kept for the reasoning.** The smallest size below: a looped
stretch, Forever included, on every surface that plays a Flip (#344); one page
painted, complete, beneath a range of pages, kept as strokes and painted as it
plays (#346); Loop and Keep under in the editor (#348); and the card itself,
drawn and then waving, in both editors' Ideas (#349, #365). The loop's
controls were redesigned after, as a trim frame on the strip (#352, #353,
#356). The other two sizes, two layers or a stack, are still 4 idea 2 and 6d.

THE IDEA. Blooby's trading card draws itself (a Draw-on page), then Blooby
waves in its window for about six seconds, then the whole thing starts over. It
shows off Draw-on and the wave in one piece, and it needs two things Flip does
not have:

  * LOOP A STRETCH OF PAGES. Mark pages 2 to 11 and say how long they repeat
    (times or seconds); Flip plays them on repeat, then carries on. It is
    Hold-a-page's big brother. Like hold, it must be serialised with the post so
    every player (link, gallery, library, in-post) plays it the same.
  * A PAGE THAT STAYS UNDERNEATH. Each Flip page carries its own strokes, so ten
    waving pages would each have to hold the whole card -- about 4,500 points,
    ten times, past the document's ceilings. A background page that the pages
    after it are drawn over is the cel-animation model, and it is the concrete
    case 6d (layers) did not have.

THE OWNER'S READ: "I think the idea brings up layers." Three sizes, smallest
first: one background page for a stretch (one small field in the format); two
layers on every page (rough and clean, 4 idea 2); a full stack. The first plus
the loop covers the card. Both are payload-schema decisions, so: mock first.

## 6j. The Colour block, shelved, not dropped (owner, after #339)

Panels: Colour made the panels you open to work with -- the Pen drawer, the
Media card, Tune, the pickers, the Post sheet, the Library's hero -- a block of
Skribl violet (#4b2fd0 to #2c1a86), with the selected dock tool solid violet,
as an opt-in beside Theme. Built, tested and merged in #339 (7733dc3), then
taken out (owner: "I might want it back. I just don't want to bloat the app
now"): an option few would find, that every new panel had to be right in
twice.

To bring it back, revert the removal commit (the squash of the PR titled
"Remove the Colour block"); everything returns at once -- the rules, the
Panels row in every menu, the inline boot's stamp, and the suites' Colour
passes, including its own census suite. Two things to settle first:

* THE NIB on the solid violet Pen tile: dark ink in Light, and a violet pen's
  line vanishes on the violet tile. Mocked: a white nib (C), or a white nib
  with a white edge round the line (A). Undecided.
* WHETHER IT IS AN OPTION OR THE LOOK. As a hidden option it cost the most for
  the least; if it comes back, the case for it is as the default.

## 6k. Several loops in one Flip (owner, after #353: "can we do multiple loops?")

Today a Flip has ONE loop -- `loop {from, to, times | ms | forever}` -- and that
is deliberate rather than an oversight: the single object is in the document
format, in the server's validation (`skribl/validation.py`), in the shared plan
every player walks (`lib/holdtiming.js`), and in every player that walks it.
#353 kept it at one for that reason. Several loops is a format change, so it is
a project of its own, not a control.

What it would take, in the order it would have to land:

* THE FORMAT: `loops`, a list of stretches that do not overlap, read alongside
  the old single `loop` so every document already saved plays as it did.
* THE RULES, on the server and in the lib alike: no overlaps, no nesting, and a
  Forever loop only as the LAST one -- pages after a Forever never play, so a
  Forever anywhere earlier would silently cut off every loop after it.
* THE PLAN: `plan()` walks the stretches in page order, each with its own count,
  so the editor's Play, the post page, the inline players and the exports stay
  one answer.
* THE STRIP: one trim frame per loop, each chip naming its own pages, and the
  handles of two loops that meet must stay separately grabbable.
* THE PLAYERS' BYTES: the lib ships in them, so the byte ratchets will move,
  and that is the owner's call each time.

## 6l. Blooby around the app, and on dark grounds (owner, at the v319 seal; parked before the next) — BUILT

**BUILT — kept for the reasoning.** Each place was mocked in both themes, on a
phone and a desk, and picked by the owner after v322: his pen above "Draw
anything" and "Draw page 1" on an empty canvas, and his question mark where a
drawing can't be shown or the Library's list didn't load (#474); his cheer
beside "Posted!" (#476). The dark ground was answered by a badge, not a
sticker: wherever the app shows him on a page he is the Home Screen icon in
small with the whole star, which brings its own lilac, so one picture reads in
both themes and on every canvas colour (owner, of the white-edged sticker it
replaced on the empty Library: "the sticker doesn't cut it and looks bad in
both themes"). The oops and sleep poses are drawn and unused. What the owner
asked for next is 6m.

Carried as "still open" through two seals and put here by the owner, asked
before the seal after v320, so it is a plan rather than an open question.

WHERE HE IS: the Home Screen icon, on the owner's white star (#358), and the
empty Library, waving (#321).

WHERE HE COULD GO: waving above "Draw anything" on an empty canvas, cheering
after a post, and an oops on an error page. Each pose is already drawn from
his own strokes: `harness/tools/blooby.py pose()` has wave, pen, cheer, think,
oops and sleep.

THE DARK GROUND: he is drawn for paper and light grounds, and on the dark
canvas or the dark theme he needs a treatment. The owner liked the big
"bubble" sticker best, with lavender lines as the fallback; on paper and
light grounds he is drawn as he is.

Build it as one pass: mock each place, phone and desktop, both themes, before
any of it.

Asked again in the cleanup before the seal after v320, "does blooby celebrate
when you post?" -- he did not then; a post said "Posted!" and nothing more --
and the owner's answer was "keep it parked until after the audit". He cheers
now (#476), and START-HERE puts him on the device check.

## 6m. The first hello: Blooby on his star, then the mark that writes itself (owner, after #476 and v327) — BUILT

THE ASK, the night the cheer merged: "make a blooby waving start small then
emerge at full screen. Animate him waving the whole time. Keep star background
logo and start blooby small and grow full size -- show multiple
interpretations and iterations of your perspective on what that means. Mock it
and think kind and cool. ... As a .skribl"

WHAT EXISTS: seven takes, each a real Flip drawn with the pen through the real
editor by `harness/tools/make_grow.py`, on a 9:16 canvas in the icon's lilac.
The whole star is the page underneath, drawn once; Blooby is redrawn a little
bigger on every page, his arm at the next step of the wave; at full size his
wave loops forever, one wave a second at 12 pages a second. The owner has all
seven as .skribl files (Flip, ⋯ → Open a backup) and a filmed mock. Measured
from the takes as drawn here:

    take                          pages   pen points   full size at
    A1  even                         49       26,247        2.1 s
    A2  eased                        49       28,929        2.1 s
    A3  eased, settle and twinkle    51       30,944        2.2 s
    B   pops up from a dot           39       24,227        1.2 s
    C   walks up to you              65       28,614        3.4 s
    D   draws himself, then grows    46       27,975        9.6 s
    E   the whole logo grows         34       40,445        1.8 s

D's drawing-in replays at the pace its pen events were sent, about eight
seconds on a loaded box; redrawn on a quiet one it comes out quicker. A3 is
2.3 MB as a .skribl, 0.4 MB gzipped.

CHOSEN, by the owner at the v323 seal (asked "what does all yes say yes to?"
first, then picked):

* WHICH TAKE: C, "walks up to you". "I like the one where blooby walks in from
  far away. he's small and he walks in to be big." Not the default A3.
* SPEED: "just right", as drawn: about 3.4 s to full size.
* WHERE HE LIVES: the first time Skribl opens on a phone, growing to full
  screen and waving, then fading into the canvas; once only, a tap skips him,
  a still hello under Reduce Motion, and one piece of code for both editors.

NEXT: the mock, before any of it is built: C on the first open, light and
dark, phone (402px) and desk, beside today's empty canvas; measured, including
how 3.4 s feels as a first hello and that a tap skips him at once.

MOCKED, the same night, on the real Pad page in the real in-post player, phone
402x874 light and dark. What the owner's eye found, and what fixed it:

* "SEE THE WHITE IN THE STAR MISSING": at full size Blooby stood below the
  star's middle, his feet and shadow on lilac beside its narrow bottom point.
  He was 0.70 of the width tall on a star reaching 0.5; the icon has him barely
  taller than the star's reach. Fixed by the icon's share (0.525) and standing
  him 0.087 of the width higher, where the star is 76 px wide each side of his
  feet against his shadow's 59. The bigger-star alternative was mocked too; its
  side points run off the screen, the white band turned down when the takes
  were first drawn.
* "THE STAR EDGES LOOK BLURRY": the band of light round the star (soft, with a
  round blob at each tip) is gone; the white fill now reaches the corners (456
  lilac device pixels inside the star at 3x before, 0 after, the count first
  shown to read 0 on a painted solid star); and the player draws at most 2
  pixels per point where an iPhone shows 3, so the hello draws at the phone's
  own 3. Only the hello: feeds and the Gallery keep the cap.
* The tool's switches for all of this are in `harness/tools/make_grow.py`'s
  docstring. Mock films did not play in the owner's viewer; GIFs rendered page
  by page through the player at 3x did.

ALSO DECIDED, AND BUILT: Blooby comes off the empty canvas ("It's too much"), on both
editors: the words stay, and sit at the canvas's middle without him (40 px
below it with him). So the hello fades into the canvas rather than shrinking
into a badge.

SAID YES TO ("all yes on the hello") and BUILT after v323: the star as
fixed, sharp at 3x, one wave then the fade, a tap skips, a still hello under
Reduce Motion, one module for both editors (lib/hello.js,
`_skribl_hello.html`, brand/blooby-hello.json; verify_hello). The badge came
off first.

THE SECOND ROUND, after v327. The owner: "his background looks super low
resolution. and it just doesn't grab me. since it's the first thing and first
time - it has to be awesome and kind"; "shouldn't he be on laptops too - any
first time?"; "weird nubs on the edge of star tips"; "I was hoping for a super
crisp look, but it looks kind of blurry". Mocked as four takes on his star,
and the owner: "C looks good". C was built, and before it merged the owner
asked whether the first hello should be the brand itself, written and then
evaporating. Mocked twice more, the second time as the app draws its mark:
M1, the dot bounces in, and M2, Blooby lands on the i. The owner: "I like
m1", then of its dot, "It's to the right?", then "all yes". BUILT, as M1
(C never shipped):

* The mark writes itself: the header's own mark, the same one stroke and even
  line, laid down by the real pen in the sweep's colours, Skribl purple to the
  accent blue (1.6 s). The i's dot drops in, stretched as it falls and
  squashed as it lands, bounces, and rests over the i (0.75 s). Then the ink
  lifts away in the order it was written, rising a little and softening, and
  the canvas shows through as the last of it goes (0.9 s). About 3.4 s, and
  9 KB as served where Blooby's star was 299.
* THE WINK (after v327, the owner: "it's just a little flat", then, of four
  more ideas mocked beside it, "A, the wink. build it."): settled over the i,
  the dot closes like an eye and opens again, half shut, a line, half open,
  then rests (a third of a second more, the dot's part 1.08 s). The first
  round (pen pressure, a sheen, a splash) was "now" still, "none of those
  really capture what I was looking for"; side-eye, a tardy dot and a hand-off
  onto the pen were the others in the second.
* On the page's own ground, light or dark, as under the header's mark.
* The dot over the i, in the header too: before the skew its middle is
  straight above the i's top. It sat 1.3 units right, which only showed once
  the mark filled a screen. `harness/tools/make_hello.py` draws the hello from
  the template's own paths, so the two cannot drift.
* Sharp: the box on whole screen pixels and the drawing a whole number of its
  pixels to each, twice the screen's where the drawing stays within 8 million
  pixels (laptops, smaller phones) and one for one past it.
* Every first visit, on any screen; never in a composer's frame. A tap, a
  click or any key skips it, and the key does nothing else. Someone who met
  Blooby meets the mark once. The visit it comes, the button cards' first note
  waits for another.
* The replay link (owner: "Yes to the replay link"): an address with
  ?hello=again, on the Pad or Flip, plays it again whether or not it was seen,
  and every reload of that address plays it again.
* Its ground first (after v327, the owner: "on a reload it goes to the canvas
  first, then goes to the skribl cursive"): the page's head decides whether it
  comes before the first paint and lays its ground over the page, so the
  canvas is first seen as the ink lifts. The ground stays while the page's own
  scripts come, as an app's launch screen does, never past them by more than
  0.3 s, and goes by itself at 8 s if the hello never runs.

LEFT, named:

* The Blooby card's title, in the two help demos that draw the card
  (blooby-card, flip-blooby-card), is a drawing of the mark with its dot at the
  old spot. Its tool reads the new spot; the demos take it when they are drawn
  again (drawn again after v327: the dot over the i on both, read off the
  drawings by verify_helpdemos).
* A Flip whose loop a viewer turns off (the full-screen bar, the Library)
  ended on its first page, not its last: at its very end the player's clock
  comes round to page one (fixed after v327: the player ends every Flip on
  its last page whole, as the editor does, and the hello no longer asks for
  the last moment itself).

Not tested here: the iPhone's engine, SF and Segoe UI (verify_hello measures
it in Chrome).

## 6n. How it works: show it, hand over the pen, keep the manual for looking things up (3 and 4 built)

ASKED after the hello mock: does How it works make sense, and should it be
reimagined? Measured on the Pad and Flip, phone and desk: it opens on a
2,726-word manual (Flip's 4,125), 56 and 64 entries in 12px text, one step a
155-word sentence, desk lines past 100 characters; the examples sit behind one
bar, two to a row about 180 px wide on a phone, three of the first being
pictures of the app's own screens. What works: the examples are real drawings
in the real player, Try it, search, nothing loads until asked, stills under
Reduce Motion, contrast 5.6:1 light and 6.3:1 dark, all 19 examples named.

WHAT THE BEST OF THEM DO (looked up at the owner's ask): people learn by doing
(Apple's onboarding guidance; NN/g's study of 70 people on 4 apps: 91% task
success after a tutorial, 94% after skipping it); help belongs at the tool, once
and sparingly (Apple's tips; Duolingo's hints in the moment); short demos with
a way straight into the tool (Adobe Fresco, FlipaClip); the manual searchable
and out of the way (Procreate's handbook). Looom, beautiful and award-winning,
is the warning: controls that feel obtuse at first get learned from outside
courses.

THE PROPOSAL (the owner picked layout 1, Watch first, from a mock of three:
1 Watch first with Look it up as the second tab, 2 Look it up first, 3 both on
one page):

1. First open: Blooby's hello (6m), the only thing shown uninvited.
2. Help at the tool: the first time a tool is picked, a small card above the
   tools plays its example with one kind line and "Got it"; once only, never
   over the canvas.
3. How it works opens on Watch: the examples big, one at a time, swipe for
   the next, Try it hands over the pen; chips for Start, Tools, Ideas.
4. Look it up: search and short answers, one or two sentences each, "More"
   for the rest, 15-16px text.

Goes away: the manual as the first screen, the steps that repeat the Start
examples, app pictures too small to read, 12px text. Flip shares all of it
(one help drawer and one examples module today). Order: 3 and 4, then 2,
after the Blooby work. NEXT: a mock of 2 and 3 beside today's, phone and desk,
both themes.

BUILT, 3 and 4 (layout 1, after v323): two tabs under the title band, Watch
and Look it up, and every opening starts on Watch at the top. Watch: the
examples big, one under another on a phone and two to a row on a desk (the
mock's layout; a swipe from one to the next is not built), chips, Try it, and
on a tool's card "More about" it, which opens its entry in Look it up. Look it
up: search, one sentence on how Pad and Flip relate, each entry its name and
first two lines with More for the rest (every word stays in the entry, so a
search still finds and shows it whole), 15-16px text; Make a Skribl last,
closed. The bar and the sheet it opened are gone, and their previews with
them. One help drawer and one examples module, so Flip has all of it. Left: 2,
help at the tool.

Whichever home, he plays in Skribl's own player (the takes were filmed in the
in-post player, `inlineplayer.js`), so "drawings that draw themselves" is the
greeting itself. Shipping the file into the app is the payload-size question
above: `lib/pointpack.js` keeps a point in four characters.

## 6o. The ⋯ menu, smaller and kinder (owner, after v323: built)

ASKED: "What about a crowded … menu? Is there a way to consolidate that menu?
... Could drafts and backups be one choice each?" Measured on the owner's
402x874 phone: fifteen equal rows at 14px over 12px, 769px of the screen,
and it still scrolled, with Report a problem, Tips, Theme and Canvas 299px
below the bottom. It scrolled on a desk too. Nothing counts which buttons
people press, so "used most" is a judgement: Export, saving a draft, New and
the Library.

THE MENU NOW (the mock, then "I like it all. Yes to all"): which editor, as
the app's sliding tint; four tiles, New, Save, Export, Library; four rows,
How it works (still first and tinted), Your drafts, Public gallery,
Settings; Report a problem and the version at the foot. 540px on the phone,
no scroll on either screen, names 16px over 14px, every target 44px. One
partial for both editors (`_skribl_menu.html`) and `lib/menupages.js` for its
two pages: New Skribl (the canvas shape, then one tap to start; Undo brings
the drawing and its shape back) and Settings (Theme, Tips, Canvas). Drafts
and backups are one row: Your drafts holds this drawing's name and Save,
every saved draft, and Save as a file / Open a file. How it works' tabs and
chips became the sliding tint too ("Are they consistent with other choices?").

Not built, and asked about: a count of which buttons are pressed (private,
in Skribl's own database; only with the owner's yes), and naming the
drawing from the header, which has no name in it today.

AFTER IT WENT LIVE (owner: "It looks good"): Settings in the menu wears a
gear, the header's sliders are named Tune on both editors, and the first Save
of an unnamed drawing asks for a name, the date name filled in and selected.

NEXT, IN THIS ORDER (owner, after v323), and since done (6p builds Hold to
learn, Draw along, Show me and the "?"): "finish the … first. Don't start on
how it works until we're done with …". When the menu is merged and the owner
is happy with it, come back to How it works (6n). Its open ideas: Hold to
learn (press and hold any control for a card with its example), Draw along
(an example plays faintly on your own canvas to trace), "Show me" (ask in
your own words and the real button glows), help when stuck, a quiet "?" in
both editors, a "Things to try" list, and accessibility under all of it. The
owner found layout 1 better but still "difficult to use" and "pretty generic
thinking"; the last proposal put Hold to learn and Draw along first.

## 6p. Help in four layers (owner, after v323: "Can we combine them so we get the best, most helpful yet unobtrusive?"; pieces one, two and three built)

Three pitches (Ask, Hold to learn, the little book) were joined into one help
that stays quiet until reached for, quietest first: ON THE BUTTON (hold it
on a phone, rest on it on a desk: its card, with its example), ASK (How it
works becomes a field in your own words, "New here? Watch Skribl in a
minute", what people often ask, and Show me, which lights the real button and
opens that same card), THE LITTLE BOOK behind "New here?" (one idea a page,
Draw along from its pages), and NAME EVERY BUTTON (? on a desk). The only
thing that appears unasked is a first-time note, once.

PIECE ONE, BUILT: lib/learncard.js. Holding keeps every job it had (owner:
"how will that affect buttons you hold already like moving pages on flip?"):
Flip's pages, the slider's - and + and the x1 badge get their card from their
name tag. Flip's sliders have no - and + (Pad's do, on a desk); noticed
here, not changed.

PIECE TWO, BUILT: lib/ask.js (the Ask mock, "All yes"). How it works is one
field; a sheet on a phone, a dialog in the middle on a desk. Thirteen how-to
answers to start (each editor sees its own), written as steps with Show me;
the rest come from the entries, with everyday cousins of the words. A card's
More asks Ask for the button.

PIECE THREE, BUILT: lib/book.js and lib/drawalong.js (the little book mock,
"Yes to all as long as it's kind"). New here? opens the little book: one
idea a page, its example playing (Pad six pages, Flip five). Draw along
lays the cat's real strokes on your canvas one at a time; any stroke counts.
It never opens by itself. NEXT: more Draw along drawings (one per tool, as
the examples grew), Draw along on Flip across pages, and more answers over
time, from what people type and find nothing for (nothing typed leaves the
app today, so that needs the owner's say).

## 6q. Blooby as the S: the owner's icon, filed, not built in (owner, after #627)

The owner sent four renders of a new Home Screen icon: Blooby as a white S
on a lilac tile, his arm raised to the star. Asked to make it more Skribl,
Cal redrew it with the pen, and the owner: "That image looks nothing like
this. Yours is sloppy." The lesson: their clean, confident curves are the
point, so their render is used as it is and never redrawn. Shown with two
changes only, the pick was "mine with deeper edges. File it away", then
"Let's forget about that for a while."

FILED: `docs/brand/s-blooby-icon.png`, 1254px square, the render pixel for
pixel but for two changes. THE CORNERS: the black outside the rounded
corners, flooded from each corner over dark pixels and 4px more for the
rim, filled from the tile around it (push-pull) and softened 6px inside the
fill alone (an icon file is a full square; the phone rounds it). THE DEEPER
EDGE: from 0.62 to 1.06 of the way out (a squircle's distance from the
middle), eased in (to the power 1.6), the ground moves up to 72% of the way
to `#9179ff`, and the white S, arm, star and face not at all. On a light
Home Screen its edge reads 2.0:1, as today's icon does (as rendered, 1.6:1).

TO BUILD IT IN, when the owner says: the three files (icon-512, icon-192,
apple-touch-icon at 180) made from it instead of `harness/tools/blooby.py
icon`, the icon notes there, and `verify_identity` taught the new icon (it
reads today's: the star's top point over his head, the lilac beside him).
A vector from the owner would make sharper files. The small Blooby pictures
in the app stay as they are unless the owner asks. Not tested: how iOS 26
tints and relights it on a real iPhone.

## 6r. Flip's pen lands up to 2px off at the canvas's edges (measured, during #648)

Flip's canvas has a 2px frame, and since B (#648) the drawing fills the
inside of it, pixel for pixel. The pen is still mapped through the frame's
OUTSIDE: a point is read as a share of the canvas's whole box, frame and
all, so a stroke at the very edge lands up to 2px from the pen (the error is
nothing at the middle and grows to the frame's width at the edges). It was
there before B, hidden by the bitmap being squeezed the same way. The Pad has
no frame and is not affected.

TO FIX: map the pointer through the content box (the box less the frame on
each side) wherever flip.js turns a pointer's place into the drawing's units,
and the eyedropper's lens with it, with a row that puts the pen a pixel in
from each edge and reads where the ink lands, red on today's mapping first.

## 6s. The music drawer as D, four doors (owner, after #654: "I like D") — next to build

Picked from the mock (Now, D and E, the real drawer on a stand-in song:
https://claude.ai/artifact/B9Shg9YZX1zmdJ4fsmshfG). The song, Hear the loop
and the timeline stay on top; under them four tiles in a row, as the draw
drawer has them (Length, Beat, Restart, Exact times), each saying what it is
set to and opening its group underneath. More goes: what it held is in the
four, Tap the beat in Beat. The defaults the owner was offered for the rest,
not overruled: one door open at a time; Length's three choices (Skribl's
pick, Fit my drawing, Whole song) as cards with the 4 · 8 · 16 · 32 beats row
under them; shorter words inside the doors. Pad and Flip share the drawer,
so both change at once; the suites that open More, the pick or Exact times
learn the doors, red first, and the help words that say "in More" change.

BEFORE BUILDING, THE WHOLE DRAWER (owner: "now that we are doing all this
new stuff, you should probably think about the design for the drawer again
and make sure it all makes sense before we build it, then have to rebuild
it after we make changes"). Mock the drawer as it will end up, every piece
of 6t in its place, and build D only on the owner's OK, in steps toward
that one picture. What it decides, each with options and a pick: where the
click's switch sits (pick: beside Hear the loop, since it is used while
listening and checks every door's work, as a DAW keeps its metronome by
the transport); the Beat tile's words for where the tempo came from
(heard, tapped, or set by the end); songs in three (the Length row in
beats, 3 · 6 · 12 · 24 for a waltz, and a small choice of 4 or 3 beats a
bar in Beat for when the ears hear it wrong); the taller box's control
beside Magnify's - and +; the lane's height for Flip's page pictures when
the box is tall; the tiles spanning a desk; the thinner loop line. Shown
for a song in four and a waltz, the Pad and Flip, light and dark, phone
and desk. None of it needs a fifth door. Mocked on the app's own code,
the loop playing and the click heard (https://claude.ai/artifact/KTcnYw6jf2ZzAeikaAtiFe,
Today and New, the Choices with the picks). What the mock settled on its
own: the click by Hear the loop is one pill with it (a third column in the
transport pushed "Play with my drawing" out of its button on a phone); the
Beat door's picture is the timeline's beat dots, the metronome being the
click's now; a stroke's ink in the lane moves toward the lane's own words
only as far as 3:1 takes (a dark ink on the dark lane, a pale one on the
light lane); growing the box keeps Hear the loop where it was (the page
scrolls by what the box grew). From the owner's Wavebox Audio
Editor screenshots ("they may be overcomplicating things too. we want to
keep with our 4 pillars"): its effects, EQ, pitch, channel mixer, copy and
paste and recording stay out, a loop under a drawing needs none of them;
its lit selection with the rest dimmed, its handles low on the wave, its
overview strip and its tall wave on a phone are what the drawer already
has or is getting. Two things in from it (owner: "yes, they seem like good
ideas"): PINCH TO ZOOM in the mock (Wavebox gives half its wave to "Zoom &
Pan"; the timeline has no
pinch today): sideways for time, up and down for the taller box, locked to
whichever way the fingers first move, two fingers so it never fights a
finger scrolling the page, and Ctrl and the wheel or a trackpad pinch on a
desk, the - and + and the taller control staying for anyone who does not
pinch; not testable here on an iPhone. And THUMB REACH as a check: Wavebox
keeps play at the foot, so measure where Hear the loop and the click land
on a 402 x 874 phone and keep them within a thumb's reach.

THE OWNER'S PICKS, "All yes" to all ten (27 October, after the whole
drawer mock and the speed and cards mock), and the build order:
the two small PRs first (the speed choice's ends, built in #655, 6u; the
tray tools' cards, 6v), then the drawer as one PR in steps, toward the
whole-drawer mock's New:
1. D's four doors (Length, Beat, Restart, Exact times), More gone. Built
   (DECISIONS, the music drawer's four doors).
2. The draw drawer's tiles, and D's, grow to span a desk (the phone as it
   is). Built (DECISIONS, the drawer tiles span a desk).
3. The loop's edge line 1.5px and sharp (whole device pixels). Built
   (DECISIONS, the loop's edge line, sharp).
4. The click in one pill with Hear the loop, and the beat's dot lit on
   each tick. Built (DECISIONS, the click and the beat lit as heard).
5. The end sets the tempo; the Beat door says where its tempo came from
   ("83 · heard", tapped, or set by the end). Built (DECISIONS, the loop's
   end sets the tempo).
6. The taller box: one tap for twice as tall, the arrows glyph beside
   Magnify's - and +, gliding (below); the wave filling the box zoomed in
   deep; pinch to zoom. Built (DECISIONS, the taller box, the wave filling
   it, pinch to zoom); the lane grows with the box in step 7.
7. The drawing's lane shows the drawing (Flip's pages as little pictures,
   the Pad's strokes in their own inks, at 3:1 against the lane). Built
   (DECISIONS, the drawing in its lane), Flip's lane growing with the box.
8. Songs in three: the ears hear threes, and a waltz counts 3 · 6 · 12 · 24.
   Built (DECISIONS, songs in three), with Beats in a bar in the Beat door.
Then the ears' speed measured at phone pace (a Worker if it shows), and
ten of the owner's songs by ear with the click on (6t). Each step's
suites, help words, contrast census and docs ride with it.

THE GROW GLIDES (owner, on the mock: "when the waveform expanded to a
longer style it was not a smooth transition, it shook and jerked"). Read
on every frame as it was shown, the mock's grow did four things wrong, and
the build does each the other way. Its clock began before its first frame,
so the box shrank 5 to 27px before it grew (the jerk). The timeline paints
a new size on the frame after (its ResizeObserver asks for one), so every
frame of the grow showed the frame before stretched to fit (the shake).
The page caught Hear the loop up only after half a pixel of drift. And
Flip's lane went to its full height at once. So the clock starts on the
first frame; the box moves in whole pixels and the page scrolls by exactly
what it grew, read off Hear itself; the lane grows with the box; and
`lib/musictimeline.js` paints a new size in the frame it is laid out (its
ResizeObserver paints rather than asks). The drawer's suite reads the grow
on every frame, up and back, on the Pad and Flip, a phone and a desk, red
first the way the mock did it: in the mock, 28 of its 40 rows were red as
the owner saw it, and each fix undone alone turned its own rows red.

Three more for the same change (owner, with screenshots):

- THE DRAW DRAWER'S FOUR TILES SIT LEFT ON A DESK. `.dp` stops at 520px and
  the drawer is wider there, so Brush, Size, Feel and Eraser leave a gap on
  the right that the colours above them do not. On a desk they should span
  the drawer evenly, as the colours do; mock both ways (the tiles grow, or
  the gaps do) beside today, the phone unchanged. D's own tiles are `.dp`
  too, so they come out the same.
- THE LOOP'S EDGE LINE ON THE TIMELINE IS TOO THICK: 3px
  (`.mt-tl-handle::after`). Try the owner's 1.5px and 2px, on a 1x, a 1.25x
  and a 2x screen (half a pixel blurs at 1x), the grip and its 44px drag
  band as they are.
- THE TIMELINE TALLER (owner, with ACID Pro 7's + and - for track height:
  "add a little magnifying glass to the loop visual to expand it vertically
  too so it would become a bigger box showing more of the wave"). Today the
  timeline is two and a half strips tall, and Magnify's - and + zoom in time
  only. Mock a small control that makes the box taller, the wave growing
  with it (one tap taller and one back, or - and + in steps), beside today,
  phone and desk, light and dark. A second magnifier beside Magnify's could
  read as the same button, so mock a taller-box glyph beside the magnifier.
  The handles' drag band, a finger that moves up or down first scrolling
  the page, and the slim strip that follows you down stay as they are. With
  512x it shows where a hit begins. Pad and Flip share the timeline.
  The owner's research on zooming names two vertical controls, the box's
  height and a visual gain (1x to 16x or 32x). Today the wave is drawn
  against the song's loudest moment (`peaksOf`), so a soft first note after
  a quiet intro can be a pixel or two tall, just where a start is placed.
  Rather than a second control, mock as an option the wave filling the box
  when zoomed in deep (64x and up, where the wave itself shows), gliding as
  it changes, and as today at the wider zooms, so loud and quiet still
  compare (owner: yes). The deepest zoom stays 512x (owner: yes): a pixel
  there holds a few samples (more for a long loop under a long drawing),
  between the research's sweet
  spot (16 to 64 a pixel) and its one sample a pixel; past that, to 24
  pixels a sample, is for mending pops by hand, which Cut on silence,
  Smooth restart and the fades already do. The research's cache of levels
  is already in: the song's loudness once, in blocks of 128, 1,024 and
  8,192 samples.

## 6t. Skribl's ears, next (owner: "the most powerful and accurate, yet simple (4 pillars) and fast module that we can create")

The owner's friend sent three plans for hearing a loop's beat: the ACID
Beatmapper Wizard in Python, a modern one with the drums split out by an AI
model, and one for a phone, in the page. Read against `lib/musicears.js`,
most of all three is already in, and parts of it are done better. What is
left comes after D (6s), each mocked first where it shows:

- THE BEAT CLICK (owner: yes). A soft tick on each beat while Hear the loop
  plays, a switch beside Tap the beat, off at first: the Wizard's metronome
  step. An ear hears a wrong beat within a bar, which marks on a timeline
  cannot show, and it tells a person whether their taps landed. It rides the
  clock the loop plays on, not a timer, and never reaches a post or an
  export. Pad and Flip share the drawer, so both get it at once. Mock,
  as an option for the owner, the beat's dot lighting on each tick (ACID
  counts bar and beat as it plays: 6.2.000; owner: yes, as an option).
- THE END SETS THE TEMPO (from the Wizard's "click the end of the first
  bar"; owner: "all yes", mocked with the click after D). Zoomed in, a
  start let go near a beat
  stays and the beat moves to it; an end only settles on whole bars at the
  tempo there is. Let the end do what the start does: zoomed in, an end let
  go within an eighth of a beat of whole bars stays, and the tempo becomes
  the one that makes the loop exactly those bars (with a smooth restart,
  measured to the bar line, a blend's length before the handle). That is
  the Wizard's two clicks across up to eight bars instead of one. Today the
  only tempo a hand can set is Tap the beat's, to a whole beat a minute, so
  a live band or an old record between whole tempos cannot be matched. With
  the click: hear the ticks drift by the loop's end, zoom in, put the end on
  the hit. Flip's Match the beat refits to the new tempo as it does to taps.
- THE DRAWING'S LANE SHOWS THE DRAWING (from ACID's video track, the film's
  frames along the song; owner: yes, after the click). The lane marks each
  stroke when it was drawn, all in the accent (the Pad), and each page as
  long as it shows, numbered (Flip). Let Flip's pages show their own little
  pictures where there is room, and the Pad's strokes their own inks, so a
  person sliding the song under the drawing sees what is drawn on each beat.
- FAST ON A PHONE, MEASURED FIRST. `listen()` mixes the song down to one
  channel at 22.05 kHz in one go before it starts slicing (`mono()`), then
  waits on a timer between slices of 8ms, which some browsers stretch to 4ms
  or more once timers nest. Measure, on a two-minute stereo song, the longest
  the page is held and the time to a pick, on this box at full speed and
  slowed four times as a stand-in for a phone (there is no phone here). If
  either shows, move the ears into a Web Worker: the page never waits on
  them, and they run without the pauses.
- SONGS IN THREE. Built in step 8 of the whole-drawer mock, on the owner's
  "All yes" (DECISIONS, songs in three): the ears hear threes, the drawer
  counts 3 · 6 · 12 · 24 for them, and Beats in a bar sets four or three by
  hand. Left over: a round of one beat for Flip's Beat in a waltz (Beat's
  rounds there are 1 and 2 bars, as a quarter or half of a bar of three
  ends between beats; a round of a beat needs the post's `beat` to take a
  third of a bar, which the server's check does not yet), and a fast waltz
  heard at half its speed, counted in bars of two (Tap the beat sets it).
- THE OWNER'S OWN SONGS, BY EAR. With the click in, ten of the owner's songs
  played with it on; any that sound off become the ears' next cases, kept as
  timings and never committed (the real recordings stay out of the repo).
  That measures the ears on real music, which `verify_musicears`'s songs,
  every beat known, cannot.

Already in, so not built twice: one channel at 22.05 kHz; a log-spectral
flux (log(1 + 10 · magnitude), bin by bin); the kick below 150 Hz; drum hits
as bursts (many bins growing at once) rather than a 2 to 5 kHz band; the
tempo refined to a thousandth over two minutes, not read from one bar; a
beat of its own for each stretch of a band that speeds up; loops of whole
bars, 20 s at most; and the join made by Cut on silence (both ends moved
together, so the length is kept, matched on every channel) and Smooth
restart (the end's tail folded under the start, a true crossfade of the
person's length), not a zero crossing at each end or a fixed 2ms fade.

Asked and not taken, and why: the drums split out by an AI model (Demucs,
Spleeter or any model run in the page: megabytes to download inside a social
site, and slow on a phone, unmeasured here; on a server, people's songs
uploaded to a paid machine); the first downbeat taken as the loudest or the
first big hit (an intro, a pickup or a crash on bar 2 fools it: the ears
take the bar where kicks and chord changes gather, and keep intros and fades
out of the pick); a grid warped to a live drummer (DTW), when a loop is 20 s
at most. If the ears ever miss real songs that the steps above cannot fix,
the modern route is a small beat-finding model that hears the whole mix,
measured against these ears first.

## 6u. The speed choice's ends (owner, with a screenshot: "everywhere this strip is the padding on right and left side is off - not enough")

The speeds `lib/replayline.js` opens under a replay (¼× to 16× and Fit, on
the Pad, the link page, the Gallery, a post's box, full screen and the post
and drafts previews; ¼× to 4× in Flip's Tune) are one pill, `.rl-chips`,
with the Pad's and Tune's own tweaks. The pill keeps 4px inside its edge
and each speed a few px of its own (4, 6 or 8), so "¼×" and "Fit" sit
nearer the rounded ends than the speeds sit to each other, and the curve
makes it look nearer still. Mocked, each place today beside two fixes and
measured live in the viewer's fonts (https://claude.ai/artifact/8F1nLN8ZUxVCBPb5e1snL8).
Here, ends against the space between two speeds: the Pad's desk pill
16.7 and 18.7 against 27.8; Tune's 15.3 and 5.5 against 23 (on a 402px
phone its eight 44px speeds overflow the row, "Fit" about 5px from the
edge: a bug today); everywhere else 9 against 10. B opens the pill's sides
by the shortfall (+10 the Pad, +5 Tune with its speeds 40px on a phone, +4
the rest), so each speed stays centred in its purple; A gives the end
speeds the room instead, so a picked end's purple reaches the curve but its
word sits off centre. My pick B. One rule for every place, then
`player.css` re-emitted; a small PR of its own. The replay line above it,
whose bars start against its left edge, is checked the same way.

BUILT, B, in #655 (owner: "All yes"): 8px inside each end on the Pad's line,
the link page and the post's box (which keeps its own copy), 14 on the
desk pill, 11 in Tune. Measuring it found Tune's eight ran off a phone (they
share the pill evenly now), and that a 320px phone's line held the pill too
tight (it may reach past its line, never within a twentieth of the screen
of its edge). verify_replayspeed, THE PILL'S ENDS.

## 6v. How it works, made again once the look settles (owner: "it will be a big project and we should definitely wait on most of it, until things looks and function as we want")

The owner: "once we get to a place where we feel like we have the
aesthetic we like and the interface isn't going to change again, we need
to redo all the how it works videos because the entire look of the app has
pretty much evolved. probably some new ones too. we can perfect those
videos too (like the speed and effects of a click, etc.). also, double
check all the how it works folder and make sure it includes all the tools
and functions as well as nothing being stale."

Today: nineteen clips in `skribl/static/help/clips/` (each light and dark,
as MP4, WebM and a still), all made on 2026-10-18 by
`harness/tools/make_help_clips.py` and checked by `verify_helpdemos`, and
the drawings to watch in `skribl/static/help/demos/`. Since then the
drawers took the menu's paper and a size up in their words, the music
drawer gained its timeline, ears, beats and 512x (and D to come), Flip
gained Match the beat, and a desk got the bigger canvas and full screen.

When the owner says the look has settled, in this order:
- THE CENSUS: every tool and function on the Pad and Flip against the
  clips and the How it works words: which have no clip, which clips show
  an old look, which words name something that changed or is gone.
- THE TIPS, in the same census (owner: "the push for tip, or hover for
  info tip on desktop needs to be expanded and updated too"; "on a phone
  its press and hold. on the desktop it's hover for like 2 seconds"). The
  card on the button (`lib/learncard.js`): held about half a second on a
  touch screen, rested on two seconds with a mouse; its name, one kind
  sentence, its example playing itself (a phone recording for Photo, music
  and Post), More and Got it, and "?" tags every button with its card.
  Under it a mouse's name on hover and keyboard focus (`lib/tooltip.js`,
  from each title: about 141 in the templates, more made in script), and
  a first-use hint once ever (`lib/hints.js`). The cards play the same
  examples How it works plays, so making the clips again makes theirs
  again too. Which buttons have no card, which cards' words or recordings
  are stale (the music one most of all), which new controls want one (the
  doors, the click, the taller box).
- ONE CLIP FIRST, made the new way and shown light and dark for the
  owner's OK: the pointer's speed and its tap, the pacing, the framing,
  the same bar as the drawings to watch.
- THEN ALL OF THEM, the old ones made again and the missing ones made, by
  the script (polished once, so making them again later is a run, not a
  project), their weight on a phone checked.
- A CHECK that every tool has a clip, so a new tool cannot arrive without
  one.

Until then, a change that adds or changes a control brings its tip and its
hint up to date in the same PR ("words follow what the user does"); only
the sweep waits.

ALL THE TOOLS, NOT ONLY THE ROW (owner: "make sure you look at ALL the
tools because I noticed the tools on flip's ^ menu don't have them"). The
cards (`lib/learncard.js`, its CARDS) cover the Pad's three tools, Flip's
same three on its shelf and the ^ itself ("More tools"), but none of the
seven in Flip's tray: Select, Liquify, Smudge, Blur, Fill, Stamps and
Artwork. Each already has a How it works clip (select, liquify, smudge,
blur, fill, stamp, artmove), and a card names its clip, so a card made now
plays the new clip when the clips are made again: these need not wait for
the sweep. The tools' clips are 4:3, as the drawings Pen, Eraser and Shape
play are, so their cards take the drawings' stage, not the tall phone
frame Photo, music and Post use. The seven sentences are mocked with the
speed pill (the page above); a small PR once the owner has said yes; the
census then walks every control on both editors, not only the tools.

## 6w. Post it on skribls.net (owner's yes, for later: the Post sheet mock)

The owner, of the posted card: "if this sits in a social media site, how do
you get back to the timeline? ... it just kind of dead ends on the Posted
card." The card now says what to do next, Back to skribls.net among it,
when the site has named its home (`home_url`, docs/INTEGRATION.md). What it
cannot do yet is put the drawing on the timeline itself.

**Post it on skribls.net**: a button on the posted card that opens the
site's composer with this drawing already attached, the way the composer's
own Skribl button attaches one (docs/SKRIBLS-NET.md, item 4), so it lands
on the author's timeline with their words. It needs a change on the site's
side: a composer address that takes a posted drawing's id (a drawing the
person just posted, never one a link names for someone else), and Skribl's
card shown only when the site says it has one. Not built; mock it beside
the posted card as it is when the site is ready.

## 6x. A long Flip's first look (Flip next, after the posting mock's 2b B)

A Pad post's link page now shows the post's own picture before its data has
come and lays the ink under it in slices (DECISIONS, after v329, "A long
drawing's first look"). A Flip's page still waits for its whole payload.
Timed on a long Flip (60 pages of 2,400 points, a 20 MB payload): its first
page is on screen 0.2 s after its data has come (0.7 to 0.8 s with the CPU 4x
slower), so its paint is not the wait; the payload's size is, and on a
phone's connection 20 MB is seconds of an empty box.

**The picture first, for a Flip**: the card a Flip posts is its first inked
page, which need not be the page its link page rests on before Play. Where
the two are the same page (the server can know: the first inked page's
place, kept beside `pages`), show the card at once the way the Pad's page
does, cropped the same way, and let it go when that page is drawn. Not
built; mock it beside the Pad's first look when it is next.

## 6y. Flip opens a long Flip without a freeze (Flip next, after the Pad's; built)

The Pad now opens a long drawing without a freeze (DECISIONS, after v329,
"The Pad opens a long drawing without a freeze"). Flip's editor does not
yet: opening a long Flip through its own file input (60 pages of 2,400
points, 144,000 in all, a 10.6 MB file) holds the page in one task of
0.9 s on a desk and 1.1 s on a phone, 3.8 s and 6.0 s with the CPU 4x
slower. Timed by step on the desk: the page strip (buildStrip, every
page's picture painted at once) is 651 ms of the 739 the load takes;
reading the file is 72 and the page itself 42.

**The strip a few pictures a frame**: the page you are on and the strip's
places laid out at once (the strip the right length, so nothing moves),
then the pictures painted a few a frame, the ones in view first, the rest
behind them; a press on a page not yet painted paints it then. Its rows
measure the longest task against the one call on the same page, as
verify_padopen's do.

**Built** (DECISIONS, after v329, "A last look at efficiency"), with the
draft the opening writes moved into a task of its own. The longest task
went from 1.4 s to 0.33 s on a phone and from 1.2 s to 0.2 s on a desk at
this box's pace (8.5 s and 5.5 s to about 1.35 s with the CPU 4x slower).
What is left is the file's own task: reading it, the page you are on.

**Still slow on a long Flip, measured and not built: a page change.**
buildStrip makes every tile again on each one (its 60 pictures laid from
the cache, every page's signature read), about 33 ms of a 54 ms change on a
desk at this box's pace and 250 to 280 ms with the CPU 4x slower. The fix is
the strip changed in place, its classes moved, rather than made again.

## 6z. The polish run's held four, and its finish line (after the audit, Oct 29 to 30)

The owner's auditor's prompt ("Comprehensive Application Code Audit &
Optimization"), merged with the polish plan, ran as four phases: look and
measure, a ranked list of twelve (the owner: "all yes"), build, and the
finish line. Items 1 to 8 are built (DECISIONS, after v329, from "No style
rule searches the whole page" to "A last look at efficiency"). These four
were held, by the owner's yes, until after the finish line; each was
measured at phone pace (Chromium, the CPU 4x slower, 4G, 402 x 874) on main
at 92bc060.

9. **Flip on a desk: fewer buttons at once** (design, mock first; Flip only).
   Twelve buttons around the canvas look equally important (Left, Right,
   Copy, Draw, Loop, Under, Delete, Duplicate, Blank, Tween, Smear), and most
   do nothing while there is one page. The idea: the page tools stay quiet
   until there is a second page, then group by what they do.
10. **On a tablet, the Pad's canvas uses the width** (design, mock first; the
    Pad, to match Flip). At 820 px wide (an iPad held upright) the Pad opens a
    tall, narrow canvas about half the screen's width; Flip already fills it.
11. **Long replays stay smooth on slower phones** (speed; trace first). The
    two-hour stand-in (145,200 points) replays at 15 to 20 frames a second at
    phone pace and the cat at 30; at full speed both hold 60 at 1x, 16x and
    Fit. The cause is not traced.
12. **Skribl's ears never hold the page** (speed; the shared drawer). A
    two-minute stereo song at phone pace: 3.2 s to decode and 3.9 s to a
    pick, and the page held four times for more than 200 ms (the longest
    0.55 s); at full speed 0.5 s and 1.0 s, the longest hold 0.14 s. The idea
    is 6t's Worker, "if it shows": it shows on a slower phone, not on the
    owner's.

**The finish line (Phase 4), not started:** Skribl inside skribls.net for
real (a Skribl button in the reply box beside GIF, posts made there carrying
the drawing's thumbnail, the player starting as more posts load while you
scroll; 6w is the posting half); then the owner and two or three friends
trying three small tasks on their phones, the only proof that something got
easier; then How it works made again (6v), once the look has settled. Skribl
as a reply (the mock the owner has seen) is next in line after that.

**The rest of the words under 12px, the owner's call.** "The last two" (the
link page's "made with", the Library's "Have a key? Use it") were the last
two on the five pages as they open with nothing posted; both are 12px now.
Opened, with posts, about twenty style rules are still under 12px: the
Library's rows (the line under each title 11px; Copy link, Key, In the
gallery and Share 11.5px; the kind tag and the stats' and now-playing labels
10.5px, in monospace caps); Export (the file name's ending, the option notes,
the progress label, and on Flip the scope and note lines, 11 to 11.5px);
Report (its details 11.5px, its privacy line 11px); the ⋯ menu (the version
line 10.5px, the row notes 11px); How it works (the search count 11.5px, the
numbered circles 11px); and in the editors the autosave status, the zoom
readout, the pending line, Flip's small + buttons and the music bar's scope
buttons (11px), with the brand tag and the narrow screen's duration badge at
10px. Not every rule may show; the census that comes with the change says
which do. The idea: every word to 12px, sheet by sheet, mocked first since
it moves six sheets' look, each with a check like the Post sheet's ("nothing
painted in the sheet under 12px").

**Measured, not built, outside the list:** Flip's page change on a long Flip
(6y); the Pad's Undo past its three copies on a two-hour piece, a repaint of
1.5 s; the Pad's own player paints a long drawing three times (DECISIONS,
"The Pad opens a long drawing without a freeze"); a file opened on the Pad
over a drawing still in progress came up without its Keep drawing pill,
seen while writing a check and not looked into.

## 6aa. Help cards inside the drawers (owner, after #691, with a screenshot of the eyedropper and Recolor: "shouldn't these have help cards? What other tools don't have help cards?")

A help card (lib/learncard.js: hold on a phone, rest two seconds on a desk)
opens only from a button its CARDS list names: the bar's tools and Flip's
tray, Undo and Redo, Photo and music, Post, Tune, the menu, Flip's page
buttons, and three tags (Pages, Page time, the slider's Steps). Nothing
inside a drawer has one. Counted Oct 30 on both editors, every drawer open,
at 402 x 874:

- **The draw drawer** (both): Eyedropper, Recolor, the Pen/Background
  switch, eight colours and the custom one, the four tiles (Brush, Size,
  Feel, Eraser) and all inside them (four brushes, the size slider and quick
  sizes, opacity, smoothing, pressure, Flip's Draw-on, the eraser widths),
  and Clear.
- **Shape's picker** (Line, Rect, Oval, Poly), which Shape's own card names.
- **The photo drawer:** Add a photo (and what a photo brings, not counted).
- **The music drawer with a song:** on and off, remove, zoom out and in,
  Snap, the taller box, the loop's Undo and Redo, Play with my drawing, Hear
  the loop, the click, and the four doors (Length, Beat, Restart, Exact) with
  the 26 controls inside them.
- **Tune:** on the Pad 10 (Grid, Stroke layers, Mirror, Pauses, Watching
  speed); on Flip 22 (with the page speed, Motion guides, Smear's weight,
  Onion skin and its depth and tint).
- **Flip only:** the Stamps drawer's size, Artwork's bar (This page, And
  following, Reset, Done), a page's actions, How it works.

Each card shows an example to watch: a How it works drawing (demo) or a
screen clip in both themes (harness/tools/make_help_clips.py).

The calls put to the owner, defaults in brackets: (1) the draw drawer's six
first, Eyedropper, Recolor, Brush, Size, Feel and Eraser, each with an
example, on both editors [yes]; (2) Tune's tools [yes, after 1]; (3) the
music and photo drawers' (Hear the loop, the click, Snap, the four doors, Add
a photo) [yes, after 2]; (4) no card for a single choice inside a tool (a
colour, a quick size, a stepper), its tool's card names it [yes]; (5) the
seal first, then the cards [seal first]. Mock the cards' words before
building, as the tray's seven were.

The words were mocked after the v330 seal (the six on the real card, Pad
and Flip, phone and desk, light and dark), and the owner said "All yes" to
them and to an example in every card, built in two steps. **Built**: the six
cards and their words (DECISIONS, after v330, "The draw drawer's six help
cards"), the Eraser size card with the eraser drawing; then the other five
examples (DECISIONS, after v330, "The draw drawer's five examples"): Recolor
and Brush as drawings that draw themselves, the Eyedropper, Size and Feel as
phone clips, each also in How it works. Call 2's words were mocked the same
way (Tune's rows, a card per row, held on its name or its control): "I say
all yes". **Built**: the ten cards, five rows on the Pad and eight on Flip
(DECISIONS, after v330, "Tune's help cards"), with the two fixes the mock
found (a tall card's clip frame gives up its spare height so the card never
covers its row; ? puts a row's tag on its name, and its banner moves off the
tags). Three play How it works' clips (Motion guides, Smear weight, Onion
skin); the other seven's examples come next, as the draw drawer's did. The
owner then asked for a Settings switch to turn the cards off: **built**, a
row of its own under Tips (DECISIONS, after v330, "A switch for the help
cards"). Next: the seven examples, then call 3.

## 6ab. Text that writes itself, in the owner's own hand (owner, Oct 31: "How hard would it be to add text to the pad?", then "Can't we have our own font")

Words added to a drawing, written in with the pen's colour, that the replay
writes out letter by letter the way it draws everything else. The words go
in as stroke points through the step the pen and Shape already use, so the
player, a posted link and every export draw them with code they already
have. Mocked on the real Pad (Oct 31 to Nov 1); the owner's answers:

- **Where:** a fifth kind in Shape's picker, Text, on both editors (a fourth
  tool in the bar pushed Shape into the tray, and four cells ran 5 to 20px
  past a 390 to 360px phone; the picker with Text is 258px and fits from
  360px).
- **Size** S, M or L, in the pen's colour and thickness.
- **Placed while a preview, then ink**: moved before Write it, honest timing
  after (moving recorded ink is why the Pad dropped Select at v219). Undo
  takes the line back whole; the Eraser rubs it like any ink; Mirror leaves
  text alone.
- **Speed**: a slider, 1/4x to 4x, where 1x is the owner's own pace,
  saying how long the words will take ("there should be a control so you
  can choose speed").
- **The owner's own font**, drawn on a letter sheet (92 boxes, a second try
  at the nine commonest letters), with Print and Script (single-line OFL
  fonts made for plotters) as extra styles.

The order: (1) the letter sheet, **built** (DECISIONS, after v330, "The
letter sheet"): `/skribl-pad?letters=1`, ending in Post your letters;
(2) the owner drew it on their phone and posted it (Oct 31, "My letters"),
and Cal read all 92 back (`harness/tools/letterfont.py`, from the post's
link); the owner will draw it again, slower ("I did it fast to see if it
works").

**Every person's own hand** (owner, Nov 1: "Every user should have their own
font, right? That they can edit?"; "Yes to all" to the five calls, then
"Yes" to the seven of the Your hand mock): each person draws their own
letters, kept on their device; 30 to start (a to z and . , ! ?), the rest
when they like, anything not drawn written in Print; any letter changed
later by tapping it; Save a copy and Open a copy; Start over with Undo; the
owner's own hand offered to everyone as the style **Skribl**, from the set
drawn again. Two pull requests. (3) **Your hand, built** (DECISIONS, after
v330, "Your hand"): the start, the first 30, Ready, the tiles, drawing a
letter again, copies, Start over. (4) **Next: the Text tool**, with its
style row (Yours or + Make yours, Skribl, Print, Script), the one door to
Your hand from the Text sheet (Edit your hand), Speed, and the owner's set as
Skribl. (5) The polish (the iPhone's keyboard, the typing sheet on a desk).

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
