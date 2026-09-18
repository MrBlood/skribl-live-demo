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
and that stopped being true several releases ago.** NINE editor-only files —
`editor_draft`, `editor_draw`, `editor_export`, `editor_menu`, `editor_music`,
`editor_photo`, `editor_post`, `editor_shapes`, `editor_tune` — were carved out
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

## 6c. Motion Smear, aimed rather than applied (owner, v295)

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

## 6h. Nothing tells you the document budget until you post (v301)

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

**Do not "fix" it by raising MAX_TOTAL_POINTS.** The cap exists to stop a
payload that pins a phone, and the comment above it in `validation.py` says so.
The problem is that the client spends a budget it cannot see.

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
