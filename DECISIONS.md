# Decisions that are yours to confirm

## 1. New posts default to `unlisted`

`skribl/routes.py` — `payload.get("visibility", "unlisted")`, and the v132
migration backfills every existing row as `unlisted`.

**Why.** A v131 Skribl was already effectively unlisted: it had a share URL,
anyone with the link could watch, and it appeared in no timeline because no
timeline existed. Defaulting to `public` would have retroactively published every
Skribl anyone ever made into a brand-new feed — including drafts, tests, and
things shared with exactly one person.

**What it costs.** Your platform must opt posts IN. If the post UI does not send
`"visibility": "public"`, the Skribl is created, gets a working share link, and
appears in no feed. Nothing errors, so it is easy to miss.

**Recommendation.** Have your platform's post UI send `"visibility": "public"`
explicitly, rather than changing the default here. That keeps the safe default
for the standalone app and for any other API client, and makes "this is feed
content" a statement by the surface that actually knows.

**Leave the migration's backfill alone** either way. That concerns posts that
already exist, made under different expectations, and republishing them is not
something you can undo once people have seen it.

## 2. CSRF is off by default

`SKRIBL_CSRF_PROTECT=1` enables it. Off is correct standalone — the API is
unauthenticated, so there is no session to protect and enabling it only breaks
existing clients. Turning it on by default broke 24 assertions across other
suites, every one a token-less POST correctly getting a 403.

**A host that authenticates POST /api/skribls with a cookie MUST switch it on.**
Without it, any third-party page can post as the logged-in user.

**v224: this is now enforced, not advised.** Passing `current_user_id` without
a `csrf` verifier RAISES at blueprint construction. The default above is
untouched — it is the default for an *unauthenticated* deployment, which is
what standalone Skribl is — but the combination "authenticated and unprotected"
can no longer be reached by not noticing a log line. `csrf=False` is the
explicit declaration for a host whose authentication is not cookie-based, and
its existence is what makes refusing fair rather than presumptuous. See v246.

## 3. Media storage defaults to `inline`

`SKRIBL_MEDIA_BACKEND=local` externalises blobs. The default is still v131
behaviour, deliberately: a storage change to a system holding real posts should
be opted into, not inherited by upgrading.

## 4. No foreign key from `skribl_posts.user_id` to a host user table

`user_id` is an indexed integer with no FK. This keeps Skribl droppable and lets
it run standalone. The trade is no referential integrity and no cascade delete —
deleting a user leaves their Skribls addressed to a missing id. If your platform
wants cascade behaviour, add the constraint in your own migration rather than
here, so Skribl stays independent.

## 5. Segmented controls are squared (`--r-seg`), labelled actions stay pills

**This reverses a v207-era rule and is the owner's call, made deliberately.**
The old rule read "pill segment = one-of-N with sliding highlight" and carried
an explicit "do NOT unify to one shape". That rule is now narrower: shape still
carries meaning, but corner radius is no longer the thing carrying it.

**The rule now.**

> **Round = an action you press. Squared = a group you choose within.**
> **Radius follows the container, not the semantics** — a cell inside a
> segmented group takes the container's derived inner radius, whatever the cell
> happens to do.

**Why it changed.** A 999px radius is a promise a control cannot keep once it
gets small. Measured on Flip at phone width: the tool group's active cell was a
37x24 box at radius 999px — i.e. a **circle** — sitting 6px from rounded-square
tiles carrying a 12px corner. Radius had stopped encoding "this is a one-of-N
group" and had started reading as an inconsistency. `--r-seg: 12px` is the tile
radius (`.t-btn` / `.tool-open`), so a segmented group now shares its
neighbours' corner and is told apart by the thing that actually distinguishes
it: a shared container with a sliding highlight. That signal survives at 24px.

**What is squared** (`--r-seg`, inner radii derived as `calc(var(--r-seg) - N)`
where N is the container's padding — never typed):

| family | where |
| --- | --- |
| `.tool-group` | Pad + Flip tool rows |
| `.seg` | onion depth/tint, fps, mirror, move scope, loop focus, zoom — 7 in Flip, 6 in Pad, 2 shared |
| `.smooth-seg` | smoothing off/low/high |
| `.photo-fit-group` | Fill / Fit / Stretch |
| `.edge-controls` | loop start/end/step nudge groups |
| `.nudge-btn` | the cells inside `.edge-controls` |

**What stays round, and why each is not an oversight:**

* **Labelled actions** — Post, Record, `loop-btn` (Match Drawing Time / Test
  Seam / Preview Loop), `dropzone-remove`. These are 4:1 to 8:1 boxes where a
  round end reads as deliberate rather than as a circle. Post especially: the
  design direction wants it to be the one loud thing on the surface.
* **`layer-toggle`** — an on/off switch. Round toggle = on/off is unchanged.
* **`color-ring`** — a colour swatch. A squared colour dot reads as a chip.
* **Surfaces** — `.toolbar` (16px), `.menu-sheet` (16px), `.flip-menu` (14px),
  `.pagebar` (0). You do not choose *within* a surface, so they keep their own
  radii; squaring a 530px-tall menu sheet to 12px makes it look like a button.

**How to reverse it.** Set `--r-seg: 999px` in `:root` (styles.css) and every
pill returns in one line. Nothing else needs touching, and the harness pin does
not need editing either — `verify_ux` reads the resolved token rather than a
literal, precisely so this decision stays the owner's to make.

**One operational note.** Editing `styles.css` requires re-emitting the derived
player stylesheet:

    python3 harness/tools/cssgraph.py --emit harness/tools/css_live.json skribl/static/player.css

`verify_cssplit.py` fails if you forget. It caught exactly that during this work.

---

# v221 decisions

**The header names the mode, not the brand.** The app ships embedded in an
already-branded host, so Pad's gradient icon and the word "Skribl" left the
header (owner call, measured first: the brand block was 108px of a 358px
phone header). Flip had already made this exact move — no icon, mode-word
only — so Pad was the inconsistent surface, not the pioneer.

**The wordmarks are graffiti piece lockups, approved by the owner through
mockup rounds — never integrated without sign-off.** SKRIBL PAD and
FLIP MODE as stacked throw-ups: spray cloud, block shadow, ink outline,
brand-gradient fill, shine pass. Eleven pair-concepts were shown and
rejected or refined on the way; the approval chain ran mockup → style
choice → reference-image adaptation → star swap → brightness tune →
integrate. Reversal: the marks are plain inline SVG in the two templates;
replace the `<svg class="brand-mark">` blocks. The verify_ux pins check
visibility, aria-label and size parity — not the artwork — precisely so the
artwork stays the owner's to change.

**The original logo was demoted, not deleted.** The 12-point star (verbatim
polygon, still on the player's card) is now the glint in both marks, at
lavender/half-opacity by owner request. One star, three surfaces, one
family.

**The marks match the tallest header element (44px), one size everywhere.**
"The phone is not a thinner brand" already had a pin; the mark inherits it.
The size-up exposed the ≤340 tier rule catching the mark (squashed 30×30);
the fix is a deliberately higher-specificity selector, commented in place.

**Accent: consolidated, demoted, restored — the classification is the
asset.** ~43 hardcoded brand hexes were folded into tokens; a full neutral
demotion shipped and the owner rejected it as flat within one look. Restore
cost four lines because the demotion was role tokens, not scattered edits.
All three palettes are recorded in `:root`. Standing guidance for a retry:
TINTED QUIET plus one loud signature element; quiet must not ship alone.

**One tree, one hash.** `run_harness.sh` and `release_run.py` now exclude
identical generated sets (the .pg gunicorn logs had diverged, printing two
hashes for one archive), and `verify_docs`' parity guard now matches `.log`
names — the regex blind spot that let the divergence live. Volatile release
facts (hash, counts) live only in generated documents; prose that quotes
them goes stale on save, demonstrated twice at v220.

**The mark outranks a button's word, because the mark is the whole brand.**
A v210 rule hid the header mark whenever a take existed
(`.header:has(#playWrap:not([hidden])) .brand > span`). It was written for
the 108px icon+wordmark lockup, which genuinely could not share a phone
header with a take's controls. The v221 mark is 70px and that premise had
been gone for two releases, but the rule stayed — so on a phone the mark
disappeared when recording started (intended) and never came back when it
stopped (not intended), at EVERY width, including 430 where ~89px of room
sat empty. Retired. `body.recording` keeps its own hide: recording always
needs the room, at every mobile width, and that case is genuinely static.

**Narrow widths are decided by measurement, not by a media query.** A static
rule cannot tell 430 from 320. `initBrandFit()` already measured the real
gap, so the take-saved case now falls to its `brand-collapsed` shed. The
shed runs in two passes, and the second one is the point: pass A keeps the
mark and sheds Record's label, the inter-control gap, then Post's label;
if the mark STILL does not fit, pass B puts those labels back and sheds the
mark instead. Without pass B, 360 and below would have spent Post's word and
lost the mark anyway — worse than the bug. Measured outcome, take-saved:
mark seated at 375/390/430, shed at 320/344/360; no header overflow and no
floor violation at any width or state.

**Post goes icon-only at 375–390 with a take saved — a deliberate narrowing
of the v219 pin, owner's call.** v219 fought to keep Post's word down to
375px and its reasoning still holds on its own terms; but it was settled
while the take-saved state hid the mark unconditionally, so Post's word was
competing against empty space. It now competes against the mark. At 390 the
mark is 21px over-full, Record is already icon-only there, the gap step
frees 8px, and Post's label frees 47 — Post's word is the only thing large
enough to pay for the mark. A shed word leaves a labelled icon with a title
attribute; a shed mark leaves nothing naming the surface. Idle is untouched
and keeps the word everywhere. Reversal: restore the `pw >= 375` split in
verify_ux's V219 block and delete pass A of the shed in `initBrandFit()`;
restoring the CSS selector named above also reverses it, less cleanly, by
making the shed dead code for the take-saved state.

**A limiter that cannot account for a slot refuses it — 429, not 500.** The
DB-backed post reservation sets a short `busy_timeout` on purpose, so a
contended SQLite write surfaces in milliseconds as an `OperationalError`
instead of blocking. That was half a design: routes.py already treats a `None`
reservation as "refused" and answers 429, but nothing turned a locked store
into `None`, so the exception propagated out of
`post_token = _rate_reserve_post(client_ip)` and Flask answered 500. The
poster saw a server error for a Skribl that was still safely in their browser.

It stayed invisible because it needs real contention. The harness fires twelve
concurrent posts at a two-slot quota; on one fast machine that resolves, and
the suite passes. On a loaded two-core CI runner it reproduces every time —
the first CI run that ever executed the harness returned
`[201, 201, 429, 429, 429, 429, 429, 429, 429, 500, 500, 500]` against an
assertion that admits only 201 and 429. Five releases of local green had never
touched it, and CI could not report it while every job died at exit 126.

Refusing is the correct direction, and the one the assertion names: "refuses
the rest under concurrency rather than over-accepting". Handing out a slot the
limiter cannot record is the failure that matters; making someone retry while
the store is contended is what 429 already means. Quota still leaks only
downward, briefly, and the warning line says which. The post-commit tombstone
sweep is now best-effort for the same reason the janitor beside it already
was: after the commit the slot exists, and letting a sweep failure reach the
new guard would refuse a caller for a slot it actually holds.

Reversal: drop the `except sa.exc.OperationalError` in `_db_rate_reserve_post`
and inline `_db_rate_reserve_post_locked` back into it. The split exists so the
unguarded path stays callable — the harness probe used it to prove the guard is
load-bearing, since the inner function must still raise where the outer must
not.

**The Loop Detail magnifier glyph is gone, and the lead that propped it up
with it.** The zoom bar carries two pills — Loop/Start/End and 1×/2×/4×/8× —
and on a phone they split onto separate lines with room to spare. Measured on
the Pad: focus pill 171.5 + gap 10 + glyph 24 + zoom pill 179.3 + lead 24 =
408.8px, so the row needed a 409px bar and wrapped below it.

Two of those numbers were decoration. The 16px glyph and its 8px gap cost 24px,
and v210 then spent another 24px on a `margin-left` for the focus pill whose
only job was to shove it back into alignment with the pill the glyph had
displaced when the bar wrapped. Removing the glyph does not merely free its own
24px — it makes the lead unnecessary, because with nothing before either pill
they both start at the bar's left edge and align when wrapped by construction.
That is precisely what v210 was buying, now had for free. 361px instead of
409px; one line down to a ~465px viewport instead of ~510px.

It also closed a Pad/Flip divergence nobody had noticed: Flip shipped the glyph
but never the compensating lead, so Flip's wrapped rows were misaligned by 24px
the whole time. Both surfaces now measure identically.

1×/2×/4×/8× reads as zoom without an icon, and the group keeps its tooltip plus
a new aria-label, so the glyph's labelling job is done by the label. verify_ux's
"carries a magnifier glyph" pin is replaced by two that outlast any redesign:
the group says what it is, and the row stays within a 400px budget. The budget
is the load-bearing one — the suite runs at 1280px where anything fits, so a
"same row" assertion there would pass no matter how much chrome came back.

Reversal: restore the glyph span in editor_music.js and flip.js, restore
`.zoom-seg[data-role="focus"]{margin-left:24px}` inside the ≤640 media block,
and raise the budget pin above 409.

**The canvas owns the only hairline; every other surface is made by fill and
shadow.** The header carried `1px solid var(--hairline)` on top of a
translucent fill AND a 26px-blur shadow — three cues for one job. With the
canvas ring (`--canvas-ring`) and the toolbar's own border, that put three
concentric outlined rectangles at almost the same radius on screen, with the
tool group's pill inside the toolbar making a fourth, and the eye could not
tell which was the subject. The canvas is the subject. Its ring stays; the
header's is gone.

Layout was not the reason and did not suffer: `box-sizing: border-box` is
global, so dropping the border returns 2px of inner width. Measured across
320/344/360/375/390/430 in idle and take-saved, every gap moved +2px and no
policy changed — the mark still seats at 375/390/430 with a take saved and
sheds at 320/344/360, no overflow, no floor violation. The brand-fit shed is
2px more comfortable than it was.

Verified against an EMPTY DARK canvas, deliberately: that is the state with the
fewest edges on screen, where a removed border shows worst. It still reads as a
raised card there. Also checked with Flip's tune drawer open, where the panel
tucks under the header and is meant to look like one object with it — the seam
holds without the header border.

One rule, three surfaces: Pad and Flip share this `.header` (flip.css only
adjusts padding and gap) and the player inherits it through the derived sheet,
which must be re-emitted with `cssgraph.py --emit` in the same edit. Reversal:
restore the one declaration and re-emit. `--hairline` is used 41 times
elsewhere and is untouched — this is a change to one rule, not to the token.

**Pad's tool row loses its tray, not its measurements.** Flip's `.flip-tools`
has never had a tray; Pad's `.toolbar` had a fill, a border, a blur and a
shadow. With the canvas ring that was two concentric outlined rectangles
competing for the eye, and the tool group's own pill inside the tray made a
third. The canvas is the subject and keeps the only frame; the row is now bare,
as Flip's always was.

ONLY the chrome went. The layout — fit-content width, the auto margin,
max-width, gap, padding and the whole responsive ladder — is untouched, because
that ladder encodes decisions this change has no business re-opening: v217
measured 343px on one row at 375 with 8px to spare, the sizing is tuned for
360px because it is a very common Android width, and v213 chose to WRAP rather
than shrink, on the grounds that shaving the buttons puts the tap target under
the 44px minimum. Flip shrinks to 36px and then 34px at its narrow tiers. That
is the trade Pad already considered and declined, and removing a background is
not a reason to reverse it. Pad still wraps to two rows at 320-344, on purpose,
now without a box drawn around it. Row counts were measured before and after at
320/344/360/375/390/430/500/700/900 and are identical.

**Undo and redo become filled tiles, because the tray was their surface.**
`.toolbar .undo-btn` was `background: none; border: none` — correct while the
tray was behind it, since a fill inside a fill is a box in a box. Without it
they were the only two controls on the row with no affordance of their own, and
read as bare glyphs. They now carry `var(--surface-control)` on
`var(--hairline-strong)`, which is exactly Flip's `.t-btn`. Geometry is
unchanged at 40x44, so the measured tap target is preserved; only the surface
is new. This is the tier the sheet already names at `.icon-btn`: bordered =
action, borderless = tool toggle, so the row still says which controls DO
something and which SELECT something.

NOT done, and left as an owner call: Flip hides the Pen/Eraser/Shape labels
below 560px (`.tool-btn-label { display: none }`) and that, with its smaller
buttons, is how it holds one row at 320. Pad keeps its words. Adopting Flip's
ladder wholesale would drop them and shrink the tap targets — a UX decision,
not a consequence of removing a background.

**The tool row's separators go; whitespace does the grouping.** `.tool-sep` was
a 1px line with 5px margins either side, and it was doing two jobs badly:
drawing a divider in a row that had just lost every other line it owned (the
tray went in 31ed04f), and standing in for the air that actually separates
groups. Measured before removing it, a separator plus its own gaps is worth
about 15px — and the grouping margins that replace it need roughly that much
anyway. Dropping both saved 2px at 1280 and cost 6px at 390. So this is not a
width change; it is one fewer line drawn on screen, and the width is a wash.
Say so plainly, because the question that prompted it was "do we get more play?"
and the honest answer is no.

Reversal: restore the `.tool-sep` rule in styles.css and the two `<span>`s in
skribl_editor.html and skribl_flip.html. Nothing else referenced the class.

**The colour ring sits against the tool pill, and the row's rhythm is why.** The
gap property was uniform across the row; what the eye saw was not. Measured at
1280 before the change, the visible gap between painted edges ran 4px at the
left end and 24px at the right, because half the controls paint a box and half
do not — a bordered neighbour puts its edge on the gap, a bare glyph sits inset
behind its own padding. The pill against a bordered undo was the 4px seam, and
it read as crowded next to image-against-music at 24px.

Colour is the one control that can sit next to the pill without two hard edges
meeting: the ring is 34px inside a 44px button, so it brings 5px of its own air
to each side. Moving it there turns one 4px seam into two comfortable ones and
costs nothing — same controls, same count. The row now reads left to right as
what the mark looks like, what happened to the drawing, and what is on the page
or how you are looking at it, with magnify joining image and music at the end
because it changes how you see rather than what is there.

At 1280 the seams go from 4, 4, 14, 19, 18, 18, 19, 24 to 21, 27, 4, 28, 24, 24.
The one remaining 4 is undo against redo, which is the single place two boxes
touching is the point.

**On phones the row gives up grouping and keeps even rhythm.** The desktop
margins (8/14/14) cost 8px that 360-class phones do not have: at 6/10/10 Pad
needed 336px against the 328 available at 360 and wrapped, breaking a decision
this file already records — 360 is a very common Android width and the row is
sized for it, not for 375. The phone tiers therefore run 5/6/6, which lands at
326: the exact figure the v217 note records, and every seam within a pixel or
two of 12, which is what two bare glyphs produce unaided. It is not grouping,
but it is not the 2, 2, 4, 8, 8, 9, 12 it replaced either. Widen these three
numbers and 360-class phones get a second row; the ladder was measured at
1280/641/640/560/430/400/390/375/360/351/344/320 before and after.

**Undo and redo are painted square; the 44px tap band moves to the ::before.**
40x44 on Pad and 36x36-in-a-44-row on Flip both read as stretched rectangles
beside a pill and a circle — they are the only controls in the row whose exact
shape is visible, so the shape has to be deliberate. They are now square at
every tier (40, 36, 34, 32) and the tap target is not given up: it moves to
`--tap-grow`, the mechanism `.color-dot`, `.onion-tint`, `.smooth-btn` and `.pb`
have used since v205-fix. Width is unchanged at every width, so this costs the
row nothing horizontally. Reversal: drop the `height` and `--tap-grow` pairs and
the two now-shared `::before` selectors.

**Flip adopts Pad's ladder, and wraps where it used to scroll.** Flip's row was
595px against Pad's 543 for the same nine controls, and 68px tall against 58 —
the same row, looser, reading as two designs rather than one. It now takes Pad's
gap, padding, button geometry and tier boundaries wholesale: 615 -> 561 wide and
68 -> 58 tall at 1280.

The behavioural half matters more. Flip was `flex-wrap: nowrap; overflow-x:
auto`, which held one line by letting Music slide off the right edge with the
scrollbar hidden and nothing on screen saying so — the defect the 320-tier block
in flip.css already documents, in a wider band. Measured: it overflowed at 351
(332 against 331 available) and again from 316 down. Pad has always wrapped
instead. A control on a second line beats one you cannot see.

Taking Pad's spacing is what makes the wrap affordable: Flip now holds ONE ROW
all the way to 320, so the second line is rarer than the scroll it replaces. The
narrow tier moved from 344 to 359 for the same reason — at 344 it left a ragged
band where Flip wrapped from 359 to 345 and then un-wrapped, and a ladder that
wraps and un-wraps as the window narrows is worse than either policy alone.

Two smaller repairs rode along, both found by measuring rather than reading.
flip.css's `@media (max-width: 380px)` set `gap: 5px; padding: 9px 6px` on
`.flip-tools` and NEVER APPLIED: the `max-width: 640px` block later in the file
wins on source order at equal specificity, so the computed gap at 380px measured
3px. Only the widths in that block ever did anything. It is the same trap the
344-tier block calls out one tier down, and the phone gap, padding and group
margins are now declared in the later block for exactly that reason — move them
back up and they go silent again. Separately, magnify was hidden at 430 on Pad
and 400 on Flip, so between 401 and 430 one row showed eight controls and the
other nine; both are 430 now, Pad being the reference.

NOT done, and left where it is: the combined photo-and-music glyph. It is worth
40-50px and the state can live in the glyph itself (the sun fills for a photo,
the note heads for a loop, retiring both `.tab-dot` badges), but `#photoPanel`
and `#musicPanel` are two separate `.tab-panel` partials shared by Pad and Flip,
and one button cannot open two drawers. That is a drawer merge, not a CSS
change, and it belongs in its own edit.

**Image and Music become one control, and the drawer they open is a router.**
The two buttons went to a single `#mediaOpenBtn` on both surfaces, opening
`_skribl_media_drawer.html`: three rows — Add image, Add music, Zoom — that open
the EXISTING photo and music panels. A router, deliberately. Nothing about those
panels' internals changes: the fit slider, trim strip, waveforms and opacity
controls all stay where they are, which is what makes a merge of this size safe
to ship in one edit. Pad's row goes from eight controls to seven and loses 42px
at 1280 and 24px at 390 — more than the whole spacing pass in this same version
cost it.

THIS IS A RESTORATION, not a new idea. The partial, the router JS and the merged
button all shipped at v216e and passed a full harness run there; they were absent
from the v217 upload with no note saying why. The uploads are whole-tree
snapshots, so there is no revert commit to read and no reason recorded. Treated
as dropped by accident. Two fragments survived the drop and are what confirmed
it: an orphaned comment above `#imageOpenBtn` in skribl_editor.html describing a
merge that was not there, and the comment block for `initMediaRows` in app.js
with its function body gone. Both are now attached to working code again. If the
removal WAS deliberate, the partial's header is where that reason belongs.

The glyph is not v216e's. That drew the image and music icons side by side in a
50x24 box, which is wide — the point of merging is width. This cuts the music
note OUT of the image frame with a dilated mask, so the two shapes read as one
object with a seam rather than as an overlap, in a 24x24 box like every other
icon in the row.

**The status lights moved inside the glyph, and they are the same elements.**
The sun is the photo light and the OUTER note head is the music light — outer
because that head sits clear of the frame, where a lit dot reads as a light
rather than as a mark on the picture. Grey means nothing attached, green means
present, amber means remembered but the file is gone: the vocabulary the sheet
already had, unchanged.

They are literally `#photoTabDot` and `#musicTabDot`, the same ids the two old
buttons carried, moved and resized. That is the whole reason this was affordable:
a dozen call sites across app.js, editor_photo.js, editor_music.js and flip.js
write to those two elements, and not one of them had to change. Styling SVG
circles instead would have meant rewriting all of them, because SVG elements do
not implement the `hidden` IDL property — `el.hidden = true` on a `<circle>`
sets a JS property that never reaches the attribute, so a rule keyed on
`[hidden]` silently never fires. HTML spans over the glyph, positioned as a
percentage of the glyph box so they ride the icon down the size ladder.

The router's rows carry their own dots, and those MIRROR the toolbar lights
rather than deriving state independently — a MutationObserver copies `hidden`
and `.pending` across. One source of truth, so the toolbar and the drawer cannot
disagree, which is the failure this arrangement is built to prevent.

Two things the harness caught that reading would not have. A stray `}` left by
moving a rule block truncated styles.css's cascade: `cssgraph.py` emitted 20,694
chars instead of 40,451 and `verify_cssplit`'s regeneration assertion failed with
the exact number. And the light's placement rule was written earlier in the file
than `.tool-open .tab-dot { top: 6px; right: 6px }` at equal specificity, so that
rule won on source order and dropped the music light 6px BELOW its note head —
correct in the markup, wrong on screen. It is now placed after it and scoped
through `.tool-open` so it outranks it both ways.

**The harness opens a media drawer in two taps now, and the same two on both
surfaces.** Six suites drove `#imageOpenBtn`/`#musicOpenBtn` on Pad and
`#imageBtn`/`#musicBtn` on Flip; they now share an `open_media(pg, which)`
helper. Worth noting what that removed: the old pair was a naming divergence for
the same job, and `verify_tips` has a comment recording the day it caused a real
gap. `verify_parity`'s table gained the three router rows, and `verify_ux`'s
phone audit now opens the router AND both panels it routes to rather than the
two old buttons — skipping the panels would have quietly narrowed the audit.

The router does not toggle the way one button did. Clicking `#mediaOpenBtn` while
a panel is open opens the ROUTER, over the canvas; three call sites were using
the old button's toggle to CLOSE, and turning them into opens left a drawer
covering `#recordBtn`. Closing is its own `close_media()` now, and says so.

NOT done, and next: `.tool-open` is 36x44 on phones (34x44, then 32x44 at the
narrow tiers). Borderless it shows nothing, but a drawer-open or magnify-active
button paints `rgba(124,92,255,.16)` with an inset ring across that whole box —
an elongated lit pill next to the square tiles this version just squared. The
fix is the same one undo/redo took: paint square, keep the 44px band on the
`::before`.

**The light sits inside the ring, and there is no grey when nothing is
attached.** Two corrections to the version above, both from the owner looking at
it.

The dot BECAME the circle: a 6px light over a sun whose outer diameter is 3.2px
covered it completely, so the icon lost its sun and gained a blob. It is 4px
now, centred inside the ring, and the ring itself had to make room -- the sun
goes r=1.5/stroke-2 to r=2.7/stroke-1.4 and both note heads r=3/stroke-3 to
r=4.2/stroke-2.0. That widening is not decoration: at the original weights there
was no inside, the stroke ate the whole circle. Both heads move together so the
note stays symmetrical when nothing is lit. Measured after: the photo light
lands at (8.16, 8.16) against a sun centred on (8.20, 8.20), and the music light
at (22.55, 21.11) against a head centred on (22.56, 21.12).

**And the size was decided at 1:1, which is the only place it could be.** The
first pass was 3px, chosen while looking at the icon blown up six times, where
it read fine. Rendered at the size it actually draws it was very nearly
invisible -- a 3px dot is mostly antialiased edge, with a core of about four
true-colour pixels. 4px is the smallest that still reads as a light on screen
while leaving each ring a visible stroke of its own. Any judgement about a mark
this small that is made on a magnified image is a judgement about a different
picture.

The COLOURS never changed and this is worth recording because it was asked:
green is `rgb(27, 207, 143)` = #1bcf8f and amber is `rgb(255, 210, 63)` =
#ffd23f, read back from the computed style and confirmed by sampling the
rendered pixels. What looks different under magnification is antialiasing around
a small dot, plus the amber's own glow -- not the hue.

The grey empty state is gone entirely. `.tab-dot-empty` answered "is there no
media?", which is a question nobody asked of a resting toolbar, and it made the
merged button noisier than the two it replaced. Nothing attached is now simply
the icon. The `:has()` swap rule stays for the controls that still pair a grey
twin with a green one.

One more thing measurement caught: the light's small size was behind a
`max-width: 640px` query, which shrank it on PAD -- where `.tool-open svg` is
24px at every width and the ring had not shrunk at all. It is Flip that steps
its icons to 21px below 640, so that rule is scoped to `.flip-tools` now. A
media query is not a proxy for "the icon got smaller" when only one surface
resizes its icons.

**The media button says its state in colour, and the dots are gone.** The image
frame goes green when a photo is set and amber when one is remembered but its
file is missing; the note does the same for music. With nothing attached it is
the ordinary icon in the ordinary grey.

This supersedes both dot attempts above, and the reason is worth keeping because
the dots were MEASURED and still wrong. A 4px light inside a 24px icon is mostly
antialiased edge -- about four pixels of true colour -- so reading it took more
attention than a toolbar glyph is worth, and every judgement about it had to be
made on a magnified image, which is a judgement about a different picture. A
tinted half is unmissable at 1:1. It also needs no geometry of its own, so the
sun and the note heads went back to the sizes the source icons use: r=1.5 and
r=3, exactly as drawn before any of this started.

An earlier version of this file called the tint "too loud" while looking at it
enlarged. At the size it renders it is not loud, it is legible, and the earlier
note was wrong for the same reason the dots were.

NO JAVASCRIPT CHANGED FOR ANY OF THE THREE ATTEMPTS. `#photoTabDot` and
`#musicTabDot` remain the state and are still written by the same dozen call
sites; they are simply not drawn any more, and `:has()` reads them to paint the
matching half. Keeping the state in elements the app already maintains is what
made three different visual treatments cost three CSS edits between them, and it
is the part of this design to preserve if the look changes again.

One ordering detail, because both selectors match while a file is missing:
`.pending` is written after "present", so amber wins over green.

**The music note is drawn at final size, because scaling it down is what broke
it.** The composite took the 24-unit music icon and shrank it with
`transform: scale(0.62)`, then thickened the stroke back up so it stayed visible
at that size. That took the stroke-to-radius ratio from the source icon's ~0.67
to 1.0 -- and at 1.0 each stem's end cap lands exactly on its note head's stroke
centreline. Both stems meet their heads TANGENTIALLY by design, so the ratio is
the whole ballgame: at 0.67 it is a clean join, at 1.0 it is a blob, and the
blob is what "the lines overlap the circles" describes.

Redrawn natively at r=2.3 with a 1.8 stroke (ratio 0.78), no group transform.
The heads also had to move APART: at the scaled geometry they were tangent to
each other as well, and two touching rings read as one lumpy shape rather than
two notes. 5.6 apart at r=2.3 leaves a full unit of gap.

The note now sits far enough outside the frame that the mask cuts a SEAM between
them instead of biting a piece out of the frame. The scaled version was
amputating the frame's bottom-right corner and the tip of its mountain, which is
the other half of what read as "drifting" -- the two shapes were not sitting
next to each other, they were eating each other.

General lesson worth keeping: scaling a stroked icon does not scale its stroke,
and compensating by thickening the stroke changes every ratio the icon's
geometry depends on. Draw it at the size it will be shown.

**"Autosave failed" now says WHICH failure, because four words could not be
diagnosed.** The catch in `writeAutosave()` wraps the whole expression --
`localStorage.setItem(KEY, JSON.stringify(serializeAutosave()))` -- so a
QuotaExceededError, a private-mode rejection and a plain TypeError inside
`serializeAutosave()` all arrived on screen as the identical message. A report
of "autosave is failing" with a screenshot was therefore not enough to tell a
full disk from a bug, which is the wrong place for a durability warning to be.

Storage-full is now its own state and its own words -- "Storage full — not
saved" -- because it is the one the user can act on. Everything else stays
"Autosave failed". Engines disagree on the name (QuotaExceededError,
NS_ERROR_DOM_QUOTA_REACHED, code 22, code 1014) so the test is deliberately
loose. The console additionally gets the exception name and message, the total
localStorage in use, the key count and the LARGEST key, so the next report
arrives with its own diagnosis attached.

FOUND WHILE LOOKING, NOT FIXED, AND DELIBERATELY SO: `saveLocalFallback()` in
editor_post.js writes an entire drawing payload -- media bytes included -- to
`skribl_post_<id>`, a unique key per save, and NOTHING EVER REMOVES THEM.
lib/posted.js caps its INDEX at 200 entries, but the index holds metadata; the
payload blobs are unbounded. Every local save is a permanent megabyte-scale
tenant of a ~5MB origin quota shared with the autosave key, so a run of them
starves autosave for every drawing afterwards, however small. That is the most
plausible cause of the report and it is a real defect on its own terms.

FIXED, once the owner's storage listing settled what was actually happening --
and it was worse than described. `remove()` deleted the INDEX ENTRY and left the
payload behind, so deleting a Skribl from the tray freed 1KB of metadata and
stranded two megabytes that nothing could ever reach again. That is why "I
deleted a skribl from the tray and it still didn't autosave".

Three changes, cheapest first:
  * `remove()` and `clear()` now drop the payload with the entry.
  * `sweepOrphans()` deletes any `skribl_post_*` blob with no index entry.
    Nothing is lost: the tray is the only route to one, so an orphan is already
    unreachable.
  * `evictOldest()` drops the oldest local save, payload and entry together.
    This one IS destructive and is the owner's explicit call. It runs only when
    the store is genuinely full and a drawing is about to be lost for want of
    room, and it says what it did in the console. An old saved copy is worth
    less than the work on screen.

Pad's autosave and Flip's last-ditch write both call `reclaim(needBytes)`, which
sweeps first and only then evicts. Verified: a forced QuotaExceededError now
reclaims and the pill reads "Saved" instead of failing.

Still outstanding, and NOT this: on the owner's machine
`skribl_flip_autosave_v1` alone was 2,763KB -- over half the origin's ~5MB, in
one key, for one 24-page flip. Flip already degrades to a media-free "lite"
payload under quota pressure, so it is not broken, but the drawing data itself
lives in localStorage while the media bytes already live in IndexedDB. Moving it
there is the real fix for the ceiling and it is a bigger change than this one.

**The one media control is REVERTED. Image and Music are two buttons again.**
Everything above about the merged glyph, the router drawer, the status light and
the tinted halves describes code that is no longer in the tree. It is kept
because the reasoning still holds for anyone who tries this again, and because
the reason it failed is not in any of it.

The merge cost a tap. Opening a photo went from one press to two -- the router,
then the row -- and the router's own rows were not self-evident enough to pay
for that. Every media action on both surfaces got slower and less obvious, all
day, in exchange for width.

And the width no longer needed buying. The merge was drawn up when Pad's row was
563px at 1280 and wrapping at 352; by the time it landed, the same version's
spacing work had it at 316px on a phone with headroom to spare. The saving that
justified the merge had already been won by cheaper means, so what remained was
purely the cost. A control that trades a tap for pixels is a good trade only
while the pixels are scarce.

WHAT CAME BACK CHANGED, because the old placement had a bug worth keeping fixed.
The status dot was anchored to the BUTTON: `top: 6px; right: 6px`. The button is
44px wide on desktop and 34px on a phone while the icon stays 24px, so one rule
produced two placements -- floating above the icon's top edge and off its right
on desktop, drifting inward over the glyph on a phone. It is anchored to the
ICON now, `left: calc(50% + 4.5px); top: calc(50% - 11.5px)`, which lands the
dot 4px inside the icon's top-right corner on both. Measured: desktop icon
corner (34, 10) with the dot at (30, 14); phone corner (29, 10) with the dot at
(25, 14). The same relationship, which it never was before.

The ring around the dot is the row's ground now (#06070a), not the tray colour
it inherited from v205. The tray went in 31ed04f and a #171a22 ring on a #06070a
row was a faint halo around every dot.

`.tab-dot-empty` is retired with it: an empty tab no longer shows a grey circle.
It answered "is there no media?", which a resting toolbar should not be
answering, and it put two permanent marks on a row that had just spent a version
getting quieter. Reversal is in the CSS comment.

ONE THING THE ROUTER DID THAT NOTHING DOES NOW: its Zoom row was the only way to
reach magnify on a phone, where the button is hidden at 430 and below. That gap
is not new -- it existed before the merge and is back exactly as it was -- but
it is the one piece of the router worth stealing if magnify should be reachable
on a phone at all.

**The header is a 36px row on both surfaces, and tune and ⋯ lose their box.**
Flip already read this way and Pad did not: Flip draws its tune and ⋯ as bare
glyphs, Pad drew them as 44px bordered tiles with a fill. Side by side the same
two controls looked like two different design systems, and the heavier of the
two was on the surface with more in its header.

The box goes. `.icon-btn`'s border and fill were v205-fix's "bordered action"
tier and they earned their place while the header sat in a tray — the tray went
in 31ed04f, and a bordered tile on a bare header is a frame around nothing. The
class keeps its border everywhere else; only the header's two openers drop it.

36 across the row — tune, ⋯, Record, Play, Post — because that is the size
Flip's header already used and the one the owner picked looking at both. Flip's
own tune was 34, two pixels short of the ⋯ beside it for no recorded reason; it
is 36 now too.

The 44px TAP band is not given up. It moves to the `::before` via `--tap-grow`,
the mechanism `.color-dot`, `.onion-tint` and `.toolbar .undo-btn` already use.
verify_ux pins all three facts — the painted box is 36, the hit box is still 44,
and a tap 3px outside the visual box still lands on the button. That last one
matters: the ::before extends over the header, and without the stacking context
the header wins the hit test and the grown target is a fiction. Pinning only the
visual size is how a shrink quietly costs a tap target.

One number changed in place rather than being overridden:
`.header.compact .btn.play.btn-icon` carries `height` at (0,4,0), which no
row-wide rule can reach past. Its comment already said "match Play's height to
Record/Post"; the row is 36 now, so the intent is preserved by changing the
number where it lives.

Flip's back arrow followed, one step further down. It was the last bordered tile
in either header and at 44px it outweighed the wordmark beside it: the heaviest
thing in the lead was the control you press least.

It does NOT join the 36px tier with tune and the overflow menu, and that is the
point. Those two act ON the drawing; the back arrow leaves the surface entirely.
Sizing it identically would say they are peers. 32px in a muted grey reads as
chrome -- findable, clearly a control, quieter than everything beside it. Four
treatments were rendered in the running header before picking: 44 boxed (the
old one), 36 bare, 32 muted, tucked tight to the wordmark, and a hairline rule
in place of the box. The rule was rejected on principle -- it re-draws the edge
this version spent its time removing.

Tap band 44 via `--tap-grow: 6px`, verified by hit test: a point 4px outside the
32px box still resolves to the anchor.

---

## A lit `.tool-open` is square, and the status dot is anchored to the glyph

Two defects that only showed up on a phone, both fixed by making a control's
*painted* box match the shape the rest of the row settled on.

**The elongated lit state.** `.tool-open` is borderless -- colour, image, music
and magnify paint nothing at rest -- so nobody noticed its box had stayed
`36x44` / `34x44` / `32x44` while every tile around it was squared. Measured on
Pad at 390px with the colour drawer open: `[34, 44]`, filled
`rgba(124,92,255,.16)` with an inset accent ring. The only lit thing in the row
was an elongated pill standing beside square neighbours. The shape was always
wrong; opening a drawer is just what made it visible.

Now square at every tier on both surfaces, with the 44px tap band moved to a
transparent `::before` -- the same trade `.toolbar .undo-btn` and the header's
openers already take. Width is untouched, so the measured row ladder does not
move by a pixel. Verified by hit test at 3px outside the painted edge: 36px
tier, 34px tier and Flip's 32px tier all still resolve to the button.

**The dot that only fitted one surface.** `.tool-open .tab-dot` positioned
itself with hard-coded offsets that assumed a 24px glyph. Pad holds 24px at
every width, but Flip steps `.flip-tools .tool-open svg` to 21px below 640 --
so the same rule put the dot 2px *past* the corner there: 5.5px outside the
icon, 1.5px inside, reading as a mark floating beside the glyph rather than a
badge on it.

The offsets now measure from `--icon-half`, redeclared where the icon changes
size (`12px` default, `10.5px` in Flip's `<= 640` block). The dot's centre lands
exactly on the icon box's top-right corner, so a 7px dot sits 3.5px out and
3.5px in -- half nestled, half proud -- on Pad and Flip alike, at 44px, 36px,
34px and 32px buttons. The 1.5px ground-coloured ring stays: half the dot now
overlaps the glyph's stroke, and the ring is what keeps the two from merging.

**How to reverse either.** For the shape, delete the `v225: a lit .tool-open
must be SQUARE` block in `styles.css` and the three `.flip-tools .tool-open`
`height` declarations in `flip.css` -- heights return to 44 and the tap band
comes back from the box itself. For the dot, replace the two `calc()`s in
`.tool-open .tab-dot` with `left: calc(50% + 9px); top: calc(50% - 16px)`, which
is where they sat before, and drop the `--icon-half` declaration in `flip.css`.

**Follow-up, same version.** Two things the owner caught by looking at the
running app.

*The merged Play pill was 38 tall, not 36.* `.header .actions .btn` brought
Record and Post to 36 and Play came with them, but Play is not the outer box --
it sits inside `.play-wrap`, the shell that merges it with the duration badge,
and the wrap had no height of its own: it hugged a 36px button and added its own
1px border top and bottom. Measured at 1280: Record `[100, 36]`, Post
`[138, 36]`, playWrap `[92, 38]`. The wrap takes the 36 now (border-box) and the
button inside comes down to 34; the divider needs no rule, `align-self: stretch`
already follows the wrap's content box. Desktop only -- below 641 the wrap goes
transparent and borderless and the button carries its own border, so that box
was already 36.

*The dot's offset is 0.5 of the icon, not 0.375.* Half in / half out of the
ICON BOX, which is what the pre-v224 rule produced and what the owner's
reference screenshot of the old look shows. 0.375 was tried in between, on a
reading of the same phrase as half over the ARTWORK: both glyphs stop at
`(21, 3)` in their 24-unit viewBox rather than at the box corner, so 9 units
puts the dot squarely on the stroke. It reads as a mark ON the icon rather than
a badge attached to it. Recorded so it is not rediscovered as an improvement.

**Follow-up 2: the dot offset is 0.4 of the icon, and the number is the
button's, not taste.** 0.5 put the dot's centre exactly on the icon box corner
-- correct on a 44px desktop button, and what the pre-v224 rule resolved to
there. But `.tool-open` carries a 12px corner radius and shrinks to 36 and 34
on phones while the icon stays 24, so the dot ran into the rounded corner of the
LIT box. Diagonal clearance between the dot's outer edge and the corner's
painted surface, measured per tier:

| tier | 0.5 | 0.4 |
| --- | --- | --- |
| Pad desktop 44/24 | +5.67 | +9.07 |
| Pad 393-640 36/24 | +0.01 | +3.41 |
| Pad <=392 34/24 | **-1.40** | +1.99 |
| Flip 393-640 36/21 | +2.14 | +5.11 |
| Flip <=392 34/21 | +0.72 | +3.69 |
| Flip <=359 32/21 | **-0.69** | +2.28 |

Two tiers were negative -- the dot crossed the accent ring of an open drawer,
which is the state it is most visible in. 0.4 is the largest offset that clears
every tier by about two pixels. The cost is 2.4px of inward travel on desktop,
where there was never a clearance problem, paid so the dot sits in the same
place relative to the icon at every width. That is the property the
button-anchored rule could not hold, and it is the whole reason for the
re-anchoring.

---

## The tool shelf holds a fixed number of cells; the tray holds the rest

**This is a decision about process, not about a tool.** Flip's bottom row was
holding two populations out of one width budget. The document controls -- colour,
undo, redo, image, music, magnify -- are a CLOSED set. The mark-making tools are
not: pen, eraser and shape today, with select, fill and text all plausible. They
shared one shelf, so every new tool competed with undo for the same pixels, and
each addition became a fresh fitting exercise across six breakpoints and two
surfaces. Measured before the change: a fourth cell takes the pill 121 -> 158px
and wraps the row at 320, 344, 360, 375, 390 and 431.

`TOOLS` in `flip.js` is now the single place a tool is declared. The shelf shows
at most `SHELF_MAX` (3) cells; anything beyond lives in `#toolTray` behind a
chevron. **The pill's width therefore stops being a function of how many tools
exist** -- verified at 320, 360, 375, 390 and 430: 103 -> 103 and 121 -> 121 when
a fourth tool is registered.

**With three tools nothing changes.** 3 <= SHELF_MAX, so all three keep their
cells, the chevron stays hidden and the tray is never built. This was deliberate:
a tray that immediately demoted Shape to two taps would be a regression paid for
a benefit that has not arrived yet. The mechanism is dormant until a fourth tool
exists, and the row does not move when it does -- three cells is what it already
held.

**Most-recently-used, not fixed.** Once overflowing, the shelf shows the two most
recent tools plus the chevron. The active tool is always the MRU head, which is
what guarantees it has a visible cell and therefore that `positionToolSlider()`
always has a button to sit under. A tool picked from the tray is promoted onto
the shelf, so the second reach for it is one tap.

**The registry is a real entry point, not a test seam.**
`window.SkriblFlipTools.register({id, label, icon})` is how a tool will actually
be added, and it is how `verify_tray.py` exercises the overflow path -- so the
suite never has to ship a fake tool, and what it tests is what will be used.

**What this does NOT do.** It adds no tools. Fill, Text and Smudge do not exist
anywhere in the tree; Select exists on Pad only (`editor_draw.js` plus
`lib/selection.js`) and needs porting to Flip's per-frame model. The eight-cell
mock that argued for this was showing that the container holds eight, not
promising them.

**Flip only, for now.** Pad has the same three tools and the same structure, and
should get the same treatment when it next needs a fourth. Doing both at once
would have doubled the surface under test for no behaviour change on either.

**How to reverse it.** Set `SHELF_MAX` to a number larger than `TOOLS.length` and
the chevron never appears; delete `#toolTray`, `#toolMoreBtn`, the `tools` entry
in `_flipDrawerCtl`, the `.tool-tray*` rules in `flip.css` and
`harness/verify_tray.py`. `setTool()` and `activeToolBtn()` now read the registry
rather than a hard-coded roster and are worth keeping either way.

**Follow-up: Pad gets the tray, and the shelf moves to a shared lib.** The
mechanics are in `skribl/static/lib/toolshelf.js` now and both editors create one
-- rather than flip.js keeping its copy and app.js gaining a second.
`verify_surfaces.py` exists because app.js and flip.js define 57 functions with
the same names and share zero runs of six identical lines; adding a 58th by
copying would be the exact failure it measures. The CSS moved the same way, from
flip.css to styles.css, which both templates load.

The ratchet then caught the one thing left behind: extracting Pad's slider
placement into a named function took the shared-name count from 60 to 61 and
`verify_surfaces` failed. Both surfaces had arrived at an identical
`offsetLeft - group padding` by independently fixing the SAME two bugs -- a
two-button assumption that parked the pill under the wrong cell once a third tool
existed, and a double subtraction of the group's own offsetLeft. That is
precisely what the ratchet is for, so the placement moved into the lib too and
the count went back to 60.

**Two bugs this introduced, both now pinned.** The chevron is a `.tool-btn` --
it has to be, to inherit the pill's shape and the sliding highlight's geometry --
so it was swept up by the binding that calls `setTool(btn.dataset.tool)` on every
tool cell. It carries no `data-tool`, so opening the tray called
`setTool(undefined)`: Flip clamps unknown ids to the pen and merely looked fine,
while Pad assigns `tool` unconditionally and was left with **no tool selected at
all**. And the tray cells were styled `font: 600 10px/1 inherit`, which is an
invalid shorthand -- the family slot does not accept `inherit` -- so the whole
declaration was dropped and the labels rendered in the UA default face at ~13px.
Neither was caught by the first version of `verify_tray.py`, which is why it now
pins "opening the tray does not change the tool" and the computed font size, on
both surfaces.

Pad's row already wraps at 320 with three tools, so the width pin there asserts
that adding a tool does not CHANGE whether it wraps, rather than that it never
wraps. Measured: Pad 118 -> 118px and Flip 121 -> 121px (103 at 320) with a
fourth tool registered.

---

## Select is a tool on Flip, and still absent from Pad

**The owner's argument settled this, and it reversed mine.** I had proposed
Select as a third scope on Move's segmented control -- "what does this offset
apply to?" -- on the grounds that it is not a way of making marks. That holds
only while the single operation is translate. Transform accompanies Select
(scale, rotate, mirror), and Move's entire vocabulary is one `(dx, dy)` offset,
typed as `40, -12` and applied to a page or a run of pages. It cannot express a
rotation, and "and following" is meaningless for a rotation of a subset --
different strokes on every page. Bolting transform onto `mbScope` would mean
rebuilding the move bar into a transform bar, at which point "scope" is the
wrong frame entirely.

So the division is:

* **Move mode** -- translate a whole page, or a run of pages, by one offset.
  Cross-page. Typed coordinates.
* **Select tool** -- pick a subset of THIS page, then transform it. Per-page.

**Why it is safe on Flip and was not on Pad.** v219 removed Select from Pad
because Pad records a timed performance: moving points that were already
recorded made replay draw a stroke at its NEW position at its OLD timestamp.
Flip has no timeline within a page -- playback reveals strokes in index order --
so moving a point changes only where it is, never when. Flip's Move mode has
translated whole pages this way since v213. `verify_select.py` asserts Pad's
registry still does not list the tool, so a future "make the surfaces match"
cannot quietly reintroduce what v219 removed.

**Undo is an operation, not a snapshot, and that is why this port is short.**
Pad's Select had to clone the selected point objects BEFORE snapshotting, or
`strokes.slice()` aliased them and undo silently restored the moved position --
its own comment is emphatic about the ordering. Flip's `actionLog` stores what
was done, so undoing a selection move is the same translation negated and there
is nothing to alias. The entry is `{type:'selmove', idx, spans, dx, dy}` and the
object branch of `undoStroke()` now dispatches on `type` -- it used to assume
every object was a Move-mode entry and would have translated the whole page.

**Whole strokes, never fragments.** The marquee selects by GROUP, so a box that
clips a stroke takes all of it or none. Moving half a stroke would leave
`strokeGroups` accounting for points that had walked away from their run, which
is the shape the server rejects on share.

**Transform is NOT in this change.** Scale, rotate and mirror are a separate
piece of work: the handles, their hit-testing, and the live preview. The model
is ready for it -- a point is `{x, y, color, size, t, erase}` and `size` is
per-point, so a scale can scale weight along with position rather than producing
a stretched outline.

**How to reverse it.** Remove the `select` entry from Flip's tool registry in
`flip.js` and the tool is gone from both the shelf and the tray; the marquee code
and `translateSpans()` become dead but harmless. Drop `lib/selection.js` from the
Flip template and `harness/verify_select.py` to finish.

## Transform: uniform scale on corners, rotation on a grip

**Scale is UNIFORM and corners-only, and that is the model's decision, not a
shortcut.** A point is `{x, y, color, size, t, erase}` and `size` is a single
scalar. A non-uniform scale has no honest answer for stroke weight: stretch a
drawing horizontally and its verticals would have to be thicker than its
horizontals, which one number per point cannot express. Edge handles are absent
by design rather than missing. If they are ever wanted, `size` has to become a
pair -- and that is a payload change, so it is a decision, not an afternoon.

**A scale multiplies `size` along with position**, which is what makes it worth
having at all: shrink a drawing and its strokes get thinner, rather than the
same-weight outline of a smaller shape. Rotation leaves `size` alone.

**Every gesture recomputes from a snapshot taken on pointerdown**, never on top
of the previous frame. Translate could get away with compounding deltas -- it is
exact under addition, and `selmove` does exactly that -- but a ratio applied to
an already-scaled value sixty times a second walks the geometry away from the
finger, and a drag out and back would not return to where it started.

**Undo restores coordinates rather than inverting the transform.** Negating a
translate is exact; dividing by a scale ratio is not, and repeated undo/redo
would drift. The entry carries `before` and `after` arrays of `{i, x, y, size}`
for the selected points only -- one or two strokes, so tens of points.

**Still missing from the FlipaClip list this came from:** mirror, clone and cut.
All three are cheap now that the transform pipeline exists -- mirror is a
negative scale on one axis, clone is a span copy, cut is a span splice -- and
none of them needs a new handle.

**One test lesson worth keeping.** `fresh()` in `verify_select.py` clears
localStorage AND empties the in-memory document before reloading. Clearing
storage alone does not work: the live page still holds the drawing and saves on
the way out, so the draft is written back after the clear and restored by the
very reload meant to be rid of it. It now also asserts zero points afterwards,
because a polluted page turns every stroke-index assertion into a coin flip --
which is exactly how it failed, reporting "the unselected stroke was touched"
when the real fault was that the selected stroke was not the one the test thought.

## Mirror, duplicate, cut and paste live on a bar that replaces the page bar

`#selbar` appears exactly while a selection exists and takes `#pagebar`'s row --
the pattern `setMoveMode()` established. Five more actions do not fit on a 320px
phone as extra chrome; they fit as a different job for the same row. `.pb-tx`
already hides below 640, so every cell drops to its glyph for free.

**One undo shape for all four: `selframe`,** carrying a before/after pair of that
page's `strokes` and `strokeGroups`. `selmove` negates its dx/dy and a transform
restores coordinates, because both leave the arrays the same length. These do
not -- duplicate appends groups, cut splices them out, paste appends -- and
undoing an index-range edit whose indices have since moved is exactly the class
of bug this codebase keeps finding. The entry carries the arrays rather than the
arithmetic. One page's points is the same order of magnitude the redo stack
already holds.

**Cut writes to a clipboard, and that is a deliberate widening of the request.**
Asked for "cut", the narrow reading is remove-the-selection -- but that is
Delete wearing the wrong name, and a flipbook's real use for cut is taking
artwork off one page and putting it on the next. So Cut remembers and a Paste
cell appears; the suite pins the cross-page case specifically. Paste is HIDDEN
rather than disabled until the clipboard has something: on a bar this tight a
disabled control is a cell of dead width.

**Duplicate leaves the COPY selected, not the original.** The next thing anyone
does after duplicating is move the new one, and the two sit on top of each
other -- selecting the original would move the wrong artwork silently.

**A selection never crosses pages.** `go()` clears it. Spans are index ranges
into ONE page's strokes array; carried to another page they would point at
different artwork, or run off the end of a shorter one.

**A note on this file's shape, now that it has bitten three times.** flip.js is
one ~4000-line classic script with `let` state scattered through it, and
`setTool()` runs during init. Three separate crashes in this version came from
the same cause: a function called early reached a `let` declared later, threw
"Cannot access X before initialization", and killed every line of the file after
it -- taking the filmstrip, the tool shelf and every later handler with it. A
`typeof` guard cannot rescue a `let`; only declaration order can. The selection
state, the move state and the clipboard are all hoisted to the top now, and the
rule going in is: state any early path can reach belongs with the early state,
and anything touching state declared further down belongs in the load handler.

## Light mode, phase 1: the chrome's colours move into :root

**I mis-scoped this out loud and the correction is the point.** I said light mode
was "the tokens exist, it's a palette block". It was not. There were 37 tokens
and **462 colour literals outside them** -- 225 hex uses across 57 distinct
values, plus 237 rgb/rgba of which 91 were white or black overlays that have to
invert. No theme scaffolding existed at all.

Phase 1 moves 179 neutral literals into `:root` **with their values unaltered**.
All nine rendered scenes -- both editors at two widths, plus the draw drawer, the
menu, the tune sheet and the overflow menu -- came back pixel-identical, worst
channel delta 0 against a capture-noise floor of 4 measured on this machine.

**The ramp is deliberately not collapsed.** Several tokens are within a couple of
luminance steps of each other and could merge, but merging them here would be a
visual change smuggled inside a mechanical one, and the two are indistinguishable
in a diff. Phase 2 has to choose a light value for each of these anyway, and the
duplicates fall out there, on purpose.

**Two things stayed literal.**
* `#0d0f14` is the CANVAS default background. That is the document's own colour
  -- saved, shared, exported -- so it must not follow the UI theme. A Skribl
  cannot change because the person looking at it prefers a light interface.
  (The owner chose chrome-only when asked.)
* `#fff` is almost always text on a coloured fill, and white on violet stays
  white in either theme.

**White washes became a triplet, not a colour.** `rgba(255,255,255,α)` at 52 call
sites became `rgba(var(--wash-rgb), α)` so each site keeps its own alpha and a
light theme flips all of them with one line. Black `rgba()` was left alone: those
are drop shadows and scrims, which stay dark whichever way the chrome goes.

**`verify_surfaces.py` now holds the line.** It fails on any hard-coded neutral
outside `:root` in either sheet. One grey added next month is one control that
stays dark when the theme flips, and nothing else would catch it.

**A tooling note worth remembering.** The rewrite script blanked comments and
`:root` into placeholders before substituting -- comments quote colours in prose,
and `:root` is where the values are defined. Restoring them in ONE pass corrupted
both stylesheets into binary: `:root` is stashed after the comments are, so the
stashed `:root` text still contained comment placeholders, and a single
`re.sub` left raw NULs in the file. The restore loops to a fixed point now and
asserts no placeholders survive.

## Flip's draft: strokes in localStorage, media bytes in IndexedDB

**This closes the bug the owner reported as "autosave is failing on pad", and it
was not Pad's fault.** localStorage is capped at roughly 5 MB PER ORIGIN and both
editors share it. Flip was writing its media into that budget as base64 data
URLs, inflated 4/3 by the encoding -- a 30-second WAV is ~6.7 MB on its own. One
Flip draft measured 2.7 MB of the shared 5 MB, and Pad's autosave was the thing
that fell over. The reclaim-and-evict fix shipped earlier in this session treated
the symptom.

The spill to IndexedDB already existed but only as an EMERGENCY path, reached
after localStorage had refused the write -- which made a 5 MB quota the thing
standing between a user and their drawing. It is the normal path now. Measured on
the same draft: **localStorage went from 1,683,508 B to about 3,500 B**, with both
media intact in IndexedDB.

The merge on the restore side needed no design work: it was written for the quota
case and had been correct all along. What changed is that it is reached on
purpose.

**Two bugs surfaced by making the rare path common.**

*The hydration guard was a byte comparison.* It refused to merge the media if
`localStorage` differed from what it held when the read started -- but every save
rewrites `savedAt`, so any autosave landing in the gap made the string differ and
the media never came back from a restore that had done nothing wrong. It is a
per-medium check now: refuse bytes only if the session already has bytes, with
the existing name check for identity.

*"Can I spill?" tested for the library, not for IndexedDB.* `lib/draftstore.js`
loads and defines its API whether or not IndexedDB exists -- it reports the
absence by rejecting, asynchronously, long after a strategy has to be chosen. So
a browser with IndexedDB disabled took the spill path anyway, the put rejected,
and a track that would have fit in localStorage came back as "Saved without
media". `verify_fix.py` runs its whole context with `window.indexedDB` undefined
and caught it.

**I nearly broke a correct test.** `verify_fix.py` TEST 3 pins that a track small
enough to fit stays inline in localStorage, and my first move was to rewrite it
as out of date. It was not: that suite deliberately disables IndexedDB, so it is
pinning the FALLBACK contract, which is unchanged and still correct. The test was
restored and its reasoning written into it. The lesson is the general one -- a
test that contradicts a change is a claim to be understood before it is a
blocker to be removed.

**`pendingPhotoMeta` / `pendingMusicMeta` are set only on real failure now.** They
used to be set on every spill, which was right when reaching that code meant the
bytes had been dropped and wrong once it became how media is saved. Nothing
visible depended on it -- every re-add card is guarded by `&& !bgImage` -- but
`serializeFlip()` reads them for `mediaOmitted`, so the record that HAS the bytes
was stamping itself as missing them.

**Still worth doing:** the bytes go to IndexedDB as base64 data URLs, not Blobs.
`draftstore.js` stores Blobs natively, which would drop the 4/3 encoding
overhead, but the whole app handles `bgImage` as a data URL string, so that is a
wider change than this one.

## Each editor script ends by saying it got there

**The most expensive bug in this codebase, measured in debugging rounds, is a
top-level throw in `flip.js`.** The page still renders, the markup is all there,
and an arbitrary SUFFIX of the behaviour is missing -- so it presents as several
unrelated features breaking at once and sends you after whichever one you
noticed first. Four rounds in a single session, every one the same shape: a
function that runs during init reaches a `let` declared further down and hits its
temporal dead zone. `let` and `const` do not hoist the way `function` does, and no
`typeof` guard can rescue them -- only declaration order can.

So `flip.js` and `app.js` each end with one statement whose only job is to prove
they reached it, and `verify_boot.py` reads it. That beats a page-error listener
twice: it also catches a throw something swallowed, and it names WHICH file died
rather than reporting a symptom three screens away. Verified by reintroducing the
bug deliberately -- the suite failed with "Cannot access '__tdzCanary' before
initialization" instead of with a missing filmstrip.

**The rule going in:** state any early path can reach belongs with the early
state; anything touching state declared further down belongs in the load handler.

**A STATIC checker was tried first and thrown away.** A regex pass over `let`
and `const` declarations reported 512 hazards in flip.js and 866 in app.js --
almost all of them property names (`style`, `length`, `width`) and keywords
(`return`, `true`) that regex cannot tell from identifiers, plus declarations
inside function bodies it had no way to scope. Scope analysis needs a real
parser, and the dynamic check is both cheaper and exact: the symptom is always
"the file stopped", which is one boolean to test.

**One footgun found while writing the suite.** `typeof frames !== 'undefined'` is
ALWAYS true in a browser -- `window.frames` is the iframe list. On Flip a real
top-level `let frames` shadows it and the expression worked by luck; on Pad it
resolved to `window.frames[0]` and threw, which the suite then reported as the
boot path failing.

**The suite pins a real difference between the surfaces** rather than flattening
it: Flip restores a draft silently, because it persists pages, media and
background and has nothing to warn about; Pad offers a "Discard / Restore"
banner, because its autosave holds strokes but NOT media bytes and a silent
restore would present a partial drawing as the whole one.

---

## v232-v233 -- Light mode: opt-in, chrome only, and the half that greys miss

**Light is OPT-IN. There is no `@media (prefers-color-scheme: light)` rule.**
Adding one was the obvious move and it was wrong. It flips the DEFAULT for every
visitor whose OS is set to light -- which is most of them -- on an app whose
entire identity is dark: the palette, both brand marks and the accent purple
were all drawn against a near-black ground. Skribl would have changed for
everyone overnight without anyone asking for it. The rule was written, observed
to flip the harness's own headless Chromium (which reports `light`), and
removed. Following the system is one block away and documented in place above
the light ramp, but it is the owner's call about the product, not a detail of
the implementation. `verify_theme.py` emulates BOTH OS preferences and asserts
the default load is dark under each, because a rule that only misfires under one
of them is exactly what nearly shipped.

**THE CANVAS IS NOT THEMED, and that was the owner's answer to the only
question worth asking before starting.** A drawing's background is part of the
drawing -- it is exported, it is posted, it is what other people see -- so a UI
preference must never repaint it. `#0d0f14` is excluded from the palette and
from both colour ratchets for that reason, and the assertion is a real pixel
read from the middle of the canvas in both themes rather than a CSS value,
because only the bitmap can say whether a token leaked in.

**The theme has to be stamped BEFORE first paint.** The setting lives in
localStorage, which no stylesheet can read, and every script in both templates
is deferred (`verify_surfaces` pins that). Applied by `lib/theme.js`, the
browser paints a dark frame first -- a black flash on every navigation, for the
people who chose light specifically to avoid one. So a tiny inline script in
`<head>` does it, shared as a partial rather than copied into two templates
because the storage key is a contract and a second copy of a contract is a
second thing to drift. The test serves the page with EVERY external script
aborted: if the theme is still right, nothing deferred was needed to get it.

**Phase 1 moved 179 neutral literals into `:root` WITHOUT changing a value, and
that is why phase 2 was a palette rather than an archaeology exercise.** All
nine rendered scenes came back pixel-identical, worst channel delta 0 against a
measured capture-noise floor of 4. Splitting the work that way meant the risky
half was mechanical and provable, and the creative half touched one block.

**Nine surfaces stayed dark after the first pass because they are TRANSLUCENT.**
Phase 1 converted `rgba(255,255,255,a)` only; the header, the page bar, the
filmstrip well, the page-bar buttons and the autosave pill are a dark colour at
partial opacity, which no hex-literal sweep sees. They became RGB-triplet tokens
(`rgba(var(--surface-well-2-rgb), 0.78)`) across 23 call sites. **A luminance
sweep over the rendered chrome is what found them** -- the static audit had
already declared the job done.

**CHROMATIC INK IS THE HALF A GREY AUDIT CANNOT SEE.** Phase 1 moved neutrals,
because greys are what a theme obviously flips, and walked past every coloured
literal. But the danger red, the warn amber and the ok green were every one of
them chosen against a near-black ground: `#f4326f` measures **3.32:1** on the
light menu sheet, below AA for body text, and it is what "Clear all" is written
in. v233 tokenised them at their existing dark values (so dark mode resolves to
exactly the old literals, verified token by token) and restated them darker at
the same hues for light. **The ratchet for ink is stricter than the one for
greys: no literal at all**, with `#fff` (text on a coloured fill, white in both
themes) and `#0d0f14` (the canvas) the only exemptions.

**The legibility threshold is RELATIVE, and getting that wrong cost a round.**
Demanding 4.5:1 of every label failed on `.menu-version` at 4.42 -- the version
footer, deliberately tertiary, and dim in BOTH themes. Passing it would have
meant darkening the upper half of the light text ramp: breaking the mirrored
relationship on purpose to satisfy a number about something this work never
touched. What light mode is answerable for is not regressing, so every element
is measured in both themes -- a 3:1 floor, and a drop fails only if it lands
under AA and loses more than 15%. `#f4326f` went 5.5 -> 3.32, caught twice over.
White on the accent (4.35:1) is printed rather than asserted: it is identical in
both themes and older than this work, so it is a palette question about the
accent, not a theme one.

**The ramp is mirrored by RELATIONSHIP, not by arithmetic.** Inverting each
luminance mechanically gives a light theme where every contrast is technically
preserved and nothing looks right: the darkest surface is the one the eye reads
as furthest back, and in a light interface that is the LIGHTEST. So
`--surface-deep` becomes white and the ramp climbs away from it in the opposite
direction, keeping the cool blue-grey hue (~220deg, low saturation) throughout;
a neutral grey would read as a different product.

**A sweep over a hidden element measures nothing and passes.** The first
legibility pass swept a closed menu, found no neutral-ground text on Flip, and
reported a triumphant 99:1 having measured zero elements. Every sweep now
asserts the COUNT of laid-out elements before trusting its numbers.

**How the ramp is kept from rotting is structural, not a list.** Add a token to
`:root` next month, forget the light value, and that one control keeps its dark
colour while everything around it flips -- silently, and nothing else would
catch it. So the assertion is: every NEUTRAL colour token must be overridden.
That lets the accent family through automatically (it is chromatic and does not
flip by design) along with the radii and easings (not colours), with no
hand-kept exclusion list to fall out of date.

---

## v234 -- The pen palette: one list, and Riso inks instead of the UI accent

**It was two lists.** Seven `<button>`s in `_skribl_draw_drawer.html` for Pad,
and a `COLORS` array at the top of `flip.js` for Flip: the same seven hexes in
the same order, kept in step by hand, with nothing comparing them. The failure
mode of forgetting one is not an error -- it is two editors quietly offering
different colours, which nobody notices until someone switches surfaces
mid-drawing. `lib/palette.js` is the list now, both surfaces build their dots
from it, and `verify_parity` asserts they render the same colours in the same
order AND that what they rendered came from the lib rather than from a copy.

**Building the dots at runtime is what made one list possible.** Pad's click
handler is delegated on `#colorGroup`, so a dot created after load needs no
listener of its own; Flip passes an `onPick` because it also closes the drawer.
The custom picker and the eyedropper stay in the markup -- they are controls,
not colours, and they are what the dots get inserted before.

**The colours are Risograph inks.** Fluorescent pink, hot orange, acid yellow, a
printed green and a federal blue, plus paper white and a toner black -- what
small-press zines are actually printed with. What was there before was a purple
and a blue lifted straight from the UI accent, a mint green and a muddy amber:
**a drawing palette that matches the chrome is a palette that was never chosen.**
Riso inks are spot colours mixed to sit on uncoated paper rather than to pass a
contrast check, so they are strongest on the dark grounds the background
swatches default to. Acid yellow on white is nearly nothing, which is true of
the ink as well.

**The lib says WHICH swatches are dark and deliberately not what colour their
rim is.** A near-black dot on a near-black drawer is an empty hole -- but the
drawer is near-WHITE in light mode, where the dot needs no help and a light rim
would be the thing that vanishes. So `dark: true` becomes `[data-ink="dark"]`
and the rim is a themed token in CSS.

**Every swatch is named now.** Flip labelled its dots with the raw hex, because
it built them itself and had nothing else to hand. "#ff48b0" is not a colour
anyone recognises being read aloud.

## v234 -- What the colour ratchets could not see

**The `rgb()` FUNCTION form.** The neutral ratchet only looked for `#hex`, so
`background: rgb(23, 27, 35)` sat on two controls -- the brush-size tray and a
segmented row -- and stayed dark in light mode with nothing to say so. Found by
looking at a screenshot. The ratchet reads both forms now.

**Marks that are white ON PURPOSE.** `#fff` is exempt from the ink ratchet
because it is nearly always text on a coloured fill, which stays white either
way. Five marks were white against a surface that FLIPS, and simply disappeared
in light mode: the brush-size preview dot, the size-preset dots, the music
playhead, the spinner's leading arc, and the ring around the selected colour
swatch -- which meant the selected colour stopped looking selected. None of the
three ratchets can distinguish those cases from the legitimate ones; they were
found by opening the drawers and looking.

**The lesson, twice in one day:** a static audit tells you what is not a token.
Only a rendered pixel tells you what is the wrong colour. Both passes are
needed, and the rendered one has to open the drawers -- a sweep over a hidden
element measures nothing and passes.

---

## v236 -- Liquify, and why it is not called Smudge

**THE ASK CAME AS A QUESTION: "where is smudge".** It had not been built, and my
first answer was that it could not be -- that smudge is a pixel operation, the
same class as fill and text, and that all three need a new primitive in the
frame format which undo, export, the draft schema and the player would have to
learn. That is true of the USUAL implementation and it is not true of the tool.

**IT SHIPPED AS "SMUDGE" AND WAS RENAMED BEFORE IT REACHED MAIN.** The rename is
the decision worth recording, not a tidy-up. A real smudge is COLOUR TRANSPORT:
Photoshop, Procreate and Krita's Color Smudge engine sample the pixels under the
brush, carry that colour along the drag and blend it down. Blending two colours
and softening a hard edge are precisely what people reach for smudge to do, and
this does NEITHER. The family it actually belongs to is Photoshop's
Liquify > Forward Warp, Procreate's Liquify > Push, and Inkscape's Tweak tool in
"push parts of paths" mode, which displaces path nodes by a distance-weighted
delta exactly as this does.

Keeping the name would have been the cheap option, and it would have made the
control lie about itself: every user arriving with a smudge tool's expectations
would find a tool that never blends and conclude it was broken. **A control that
lies about what it does is worse than one that is merely limited.** Renaming it
also makes a future colour-blending smudge an honest separate feature rather
than a bug report against this one -- and that feature needs a raster layer in
the format, which is still the owner's call.

**AND COLOUR TRANSPORT WAS NEVER AVAILABLE HERE ANYWAY.** Blending needs pixels
to sample and Skribl has none. A page is a list of points, and that same list is
what the player replays, what export walks and what the draft stores.
Rasterising a page to blend it would kill replay outright -- a flattened image
has no stroke order left to animate.

**So this moves the GEOMETRY.** Points inside the brush are dragged along with
the pointer, weighted by distance from its centre, and the strokes bend. For a
line document that is the better instrument anyway: it moves the ink you drew
rather than averaging it into mud, and it is LOSSLESS where a raster smudge is
not -- ten undo/redo round trips come back bit-identical, which no colour smudge
can offer.

**What it costs, stated plainly:** no colour bleed. Two crossing strokes bend
towards each other but never mix, and nothing in this format can make them mix.
**What it keeps** is the entire reason to do it this way: replay, export, the
player, the draft, and an exact undo. `verify_liquify` proves it end to end --
it liquifies a page, POSTS it, and loads the result in the player, which was never
taught about liquify and did not need to be.

**THE FIRST VERSION SPIKED INSTEAD OF SMEARING, and the fix is one constant.**
At full strength a point in the centre of the brush moves the entire delta --
which lands it back in the centre for the next move event, at weight 1 again. It
rides the cursor forever, and every line the brush crosses is dragged to the
same single point. Measured on three parallel lines: all three converged to one
vertex, a hard V rather than a smear. `LIQUIFY_STRENGTH` below 1 makes the ink
LAG behind the brush; lagging, it sits further from the centre; further, its
weight drops; and it sheds off the back on its own. That is what dragging a
finger through wet ink actually does. The suite pins the PROPERTY rather than
the constant: three parallel lines must still be three lines afterwards.

**The falloff is squared, not linear.** Linear reads as a shove -- the whole
disc lurches and the rim of the brush leaves a visible crease across the stroke.
Squaring pulls the centre along and lets the rim off almost untouched.

**Undo stores COORDINATES, not a displacement**, for the reason selRestore's
comment already gives: a liquify stroke accumulates over dozens of move events at a
different weight each time, so there is no single delta to negate, and
re-deriving one would walk the artwork further from home on every cycle. Ten
undo/redo round trips are asserted bit-identical.

**A liquify stroke belongs to the page it STARTED on.** The frame index is pinned at
pointerdown, exactly as `strokeFrame` is for a stroke -- the same trap, in the
same file, for the same reason. Changing page mid-drag and re-reading `frame()`
would apply the back half of the gesture to different artwork at indices that
mean something else there, and hand undo a before/after pair for strokes nobody
touched.

**A tap logs nothing, and neither does a drag across empty canvas.** A no-op on
the history puts the stroke the user actually wants back one press further away
than they expect.

**The reach ring is dashed and the reach is wider than the brush paints.** A
solid ring that size would read as a colossal brush about to lay ink; dashed
says influence. Reach is tied to the brush slider, so the tool needs no control
of its own -- the row is already full, and "the size you draw with is the size
you push with" is one less thing to explain.

**THE TRAY EARNED ITS KEEP A SECOND TIME.** Liquify is the fifth tool and the row
did not have to be re-fitted for it, exactly as the tray was built to allow.
That is now two features that cost nothing in layout.

## v236 -- A setup step that quietly does nothing is worse than one that fails

`verify_liquify`'s `fresh()` reset the document but not the TOOL. A section that
left liquify selected made the next section's setup silently draw nothing --
`line()` liquified an empty page instead of drawing on it -- and three assertions
downstream then passed or failed for reasons that had nothing to do with what
they named. One of them passed VACUOUSLY: "undo restores the exact coordinates"
compared an untouched page against itself and reported 0 points differing.

Two changes, both of which belong in any suite that builds its own fixtures:
`fresh()` restores the pen and ASSERTS it, and `line()` asserts that the stroke
count actually went up. The suite is allowed to fail; it is not allowed to
measure the wrong thing and call it a pass.

---

## v237 -- The in-between, and what the reference photograph was actually showing

**THE OWNER ASKED FOR A REAL SMUDGE, "used to simulate motion", and then sent a
stop-motion reference:** three frames of a wire puppet, the middle one blurred.
Reading that photograph properly is what produced this feature, and my earlier
answers had all been aimed at the wrong target.

What sells that middle frame is NOT blur. It is that the blur is UNEVEN -- the
feet, which barely travelled, are nearly sharp; the arms, which swung furthest,
smear away to nothing. It is one long exposure integrating the path between two
poses, and the sharpness gradient IS the motion information.

**That is why it can be done honestly in a stroke document.** Sample the motion
between two pages at N steps and draw every step faintly. A point that hardly
moves lays all N of its copies on top of each other and stays crisp; a point
that travels far spreads them along its path and goes soft. Nobody authors the
falloff -- it is what integrating a motion MEANS. Measured in the suite: the arm
tip spans 150px across the exposure and the foot spans 2px.

**NO FORMAT CHANGE AT ALL, which is the part I got wrong three times before
getting right.** I said blur needed a raster layer; then that it needed a render
attribute the player must learn. Neither is true of THIS. Opacity already rides
inside each point's rgba() and the player already honours it, so an exposure is
just strokes -- editable, erasable, exportable, postable, replayed in order like
anything else. The player was never told about it and did not need to be.

**The blur is still available and still a decision.** ctx.filter carries a real
gaussian and it works in this engine (measured). 26 samples unblurred is most of
the way to the photograph; the faint ribbing left over reads as a DRAWN
in-between rather than a photographic one, which suits an app that looks like a
printed zine. Adding the gaussian means a render attribute the PLAYER has to
honour -- the same trap the `pressure` note records -- so it waits for the owner
to see this in the app first.

**THE POINT BUDGET IS THE HAZARD, again.** Multiplying a page by 27 is exactly
how a feature makes a drawing unpostable: the server refuses a frame over 20,000
points, and it would refuse at the moment the user tried to share, with no
earlier warning. N adapts -- a 900-point page that would have produced 24,300
points produces 14,400 instead. Third feature in a row where the cap was the
thing that needed designing around rather than discovering.

**It refuses rather than guessing.** Interpolation needs corresponding strokes,
which Duplicate-then-drag produces and two freehand redraws do not. Inventing a
pairing would produce a mess that reads as a bug in the tool rather than a limit
of the idea, so it says "An in-between needs the same strokes on both".

## v237 -- "Page 21 / 43" was clipping the Delete button

The counter cost 69px against 30px for "21/43", in a `nowrap` bar whose contents
already measured **369px inside 340** at a 360px viewport. The last button was
being cut off, and had been for some time -- found while answering the owner's
question about whether there was room for a new button, which there was, because
the new button is in the FILMSTRIP and never competed with this bar at all.

In a bar whose every other control is a page operation, directly above a
filmstrip of numbered pages, "Page" was spending real estate to say what the
context already said.

**The accessible name keeps the full sentence** (`aria-label="Page 21 of 43"`).
An abbreviation may shorten how a control LOOKS; it may never shorten its
accessible name. Both halves are asserted, so a later tidy-up cannot drop the
spoken one -- and verify_pages, which asserted `"Page " in textContent`, now
asserts the INTENT (a digit on screen, "Page" in the accessible name) rather
than the wording. A test that contradicts a change is a claim to be understood
before it is a blocker to be edited.

---

## v238 -- The autosave pill fades where it would cover a control

**It sat on the pen button, on every phone size, on both surfaces.**
`.autosave-status` is position:fixed at bottom-left and on a phone the tool row
is at the bottom too. Desktop never collides -- which is exactly why it lasted:
IT IS INVISIBLE ON THE MACHINE IT WAS BUILT ON.

**A rule for a nearby case already existed** and had the right instinct: the
pill fades while a drawer is open, because "a pill covering a destructive button
is worse than one you cannot see". It fixed the collision somebody noticed
rather than the general one. CSS cannot ask whether two boxes intersect, so the
general case needed measuring, and lib/pillfit.js measures it.

**A WARNING IS NEVER FADED.** `failed` and `partial` stay on screen deliberately
-- flip.js records why: "a warning that fades claims it was resolved". Fading one
because it happened to overlap would trade a cosmetic problem for a durability
one, silently, in the exact situation where the user most needs telling. The
overlap rule applies to the reassuring states only, and most of
verify_pillfit.py is spent on that distinction rather than on the easy half.

**The pill was already pointer-events:none**, so none of this was ever about
blocking taps -- it obscures a control without disabling it. Worth establishing
before weighing the fix, and asserted so a later change cannot make the pill
interactive and turn an overlap into a dead button.

**THE CONSEQUENCE, STATED RATHER THAN DISCOVERED LATER: "Saved" no longer
appears on a phone at all.** The owner chose fading over moving it, and on a
phone the overlap is permanent rather than occasional -- so this is a change
from "visible and in the way" to "not shown". The states that actually need
reading still show everywhere. If the reassurance turns out to be wanted on
mobile, the answer is to give the pill somewhere to go, not to weaken the rule
about warnings.

**Shared, not written twice.** Both editors show the same pill from their own
showAutosaveStatus(), and verify_surfaces counts the names those two files define
in common -- so this is a lib rather than a function added to each. The player
has no autosave and does not load it.

---

## v239 -- The in-between stalled playback, and the fix was the colour FORM

**REPORTED FROM A PHONE, on work that had already shipped to main: "it takes 2
seconds to play 3 frames".** The in-between rendered, but it could not be
played, which for an animation tool is most of the point.

**The cause.** paintStatic gives every translucent stroke its own offscreen
layer -- clear a full canvas, redraw, composite it back -- so that a see-through
stroke does not bead at its own overlaps. That is right for a stroke somebody
drew. An exposure is 27 samples of EVERY stroke, so a six-limb figure is 162
translucent strokes and roughly 486 full-canvas operations per frame. Measured:
**221 ms to render one in-between against a 12 fps budget of 83 ms**, and worse
on a denser drawing -- the owner's was worse. render() is synchronous and runs
before the next frame's timer is armed, so the PREVIOUS frame sits on screen for
the duration. That is why the stall appeared on the page before the in-between
as well as on it, which is exactly how it was reported and is the detail that
identified the mechanism.

**AND THE LAYERING WAS WRONG FOR THIS CONTENT ANYWAY.** It exists to stop a
stroke compounding at its own overlaps. An exposure IS compounding overlaps --
the density where samples pile up is the effect.

**Two fixes were tried and rejected before the right one.** Opaque samples on a
brightness ramp: 40x faster and it looks like a solid white wedge, because
opaque strokes cover rather than accumulate. Fewer samples: the cost is per
STROKE, so a six-limb figure would need about three samples to fit the budget,
which is three copies rather than a smear.

**THE FIX IS THE COLOUR FORM.** Both renderers decide whether to layer by
matching the rgba() FUNCTION form -- alphaOf here, parseStrokeAlpha in app.js,
which is also the player's renderer -- and neither matches an 8-digit hex.
Canvas honours #rrggbbaa and accumulates it either way (verified: two passes of
#ffffff21 over black give 33 then 61). **221 ms -> 5.8 ms, the same picture**
(+3.3% ink mass from the extra intra-stroke accumulation, median pixel delta 3),
with NO new field, NO renderer edit, and NOTHING for the player to learn.

**This is why it was worth looking again rather than asking.** The fix I had
lined up needed a per-stroke marker both renderers would have to honour -- the
format contract the owner has repeatedly reserved. Being pushed to find a
cheaper answer produced one that needs no decision at all. A format change is a
last resort, and "I cannot see another way" is not the same as "there is none".

**The assertion is on the COST, not on the colour string.** Teaching alphaOf to
understand hex would make exposures slow again -- not broken, just slow, which
is the kind of regression that ships. A cost budget catches that; a test on the
string would not, because the string could stay the same while the heuristic
around it changed.

---

## v240 -- A fix that only applies to NEW data is half a fix

**Reported a second time, from the same phone, after the first fix had shipped:
"it still pausing on the blurred slides".** v239 wrote the fade as an 8-digit
hex so the renderer would stop giving every sample its own full-canvas layer.
That was the right diagnosis and the right mechanism -- and it changed the
GENERATOR only. Every in-between already saved in a draft still carried rgba()
and still cost 218 ms. Measured side by side on one page: 5.2 ms as hex, 218.4
ms after rewriting the same colours back to rgba().

**I shipped it, verified it on a page I had just generated, and called it
fixed.** The verification was real and the sample was wrong: the only pages that
could show the bug were the ones that already existed, and I tested a new one.

paintStatic now carries a COST CEILING. Layering costs a full-canvas round trip
per translucent stroke -- about 1.4 ms at 816x612 -- so a frame holding more
than a frame-budget's worth of them paints direct. Old pages 218 ms -> 5.1 ms.
It covers pages saved before v239, hand-edited pages, and any future content
heavy enough to stall, none of which a generator-side fix can reach.

**The ceiling is a ceiling, not a ban**, and the suite asserts both halves: an
old-format in-between must render fast, AND a hand-drawn frame with six
see-through strokes must still get its layers. A guard that silently stopped
compositing ordinary painting would be a worse bug than the one it fixed.

**The habit worth keeping:** when a fix changes how data is WRITTEN, ask what
happens to the data already written. The people most likely to hit the bug again
are exactly the ones who hit it the first time, because they are the ones with
the old data.

---

## v241 -- Page holds were saved and then silently thrown away on load

**Found by hand, generating a demo file.** Three key poses were set to a x2 hold
so they would sit a beat either side of each in-between smear. The .skribl
contained `hold: [2, null, 2, null, 2]` -- serializeFlip writes it correctly --
and after loading, every page was back at 1.

applyPayload rebuilds each current-format frame through healFrame, and all four
of its return paths produced `{strokes, strokeGroups}`. The hold was read out of
nothing and dropped on the floor. **The same path restores the AUTOSAVE**, so a
hold did not survive an ordinary reload either -- set a page to x3, come back
tomorrow, and the timing is gone with nothing to say so.

**WHY verify_hold DID NOT CATCH IT, which is the useful part.** That suite has
thirty-odd assertions and every one of them is about WRITING: the badge appears,
the payload gains a `hold` key, unheld pages stay absent, copy/paste carries it,
the exported GIF has the right frame delays. Not one asked whether a hold comes
BACK. The feature was verified in the direction it worked.

The new assertion is a genuine round trip -- serialise, WIPE the live state,
load it back, read the hold off the restored frames. Verified by removing the
fix: it reports [1, 1, 1, 1] while the other 38 assertions stay green, which is
exactly how the bug survived.

**The pattern, twice in two days:** verify_tween proved an in-between was
correct and never asked whether it was fast enough to play; verify_hold proved a
hold was written and never asked whether it was read. **A suite that only tests
the direction a feature works will pass forever while the feature is broken.**
When something is written, test that it comes back. When something is drawn,
test that it can be played.

## v242 -- The blur inflated big objects, and nobody had measured a big object

Reported as "that looks terrible", with screenshots of a bouncing ball. It was.

The blur's halo was a MULTIPLE of the brush -- the widest pass 3.4x. On the 6px
stroke every earlier measurement used, that is a 7px soft edge and it looks
right. On a 60px ball it is a 204px cloud: the ball INFLATES instead of
smearing, and reads as a lumpy blob rather than something moving fast.

**Only one brush size was ever checked, and it was the size that hides the
defect.** verify_tween had eleven assertions about the blur and every one of
them passed while objects were being fattened by 288px, because they all asked
WHETHER there was a falloff and none asked how wide it got RELATIVE to what was
being blurred. The new checks span 8 to 120px.

The model was wrong, not just the constant. Motion blur does not fatten an
object: it smears it ALONG its travel -- which the sample sequence already did,
and which was never the problem -- and leaves the edge ACROSS the travel nearly
sharp. So the halo is a small bounded softness ADDED to the brush, and
smoothness along the path comes from sample COUNT, not from halo width.

## v243 -- A blur pass cannot carry a colour it has no bits for

Found while making a demo: an orange ball grew a RED halo. Measured off the
canvas rather than guessed -- a plain ball reads (255,176,32), the same ball
blurred peaked at (240,134,2). The blue was not dimmed. It was gone.

Canvas composites through PREMULTIPLIED 8-bit alpha: a channel is stored as
round(channel * alpha). A halo pass at alpha 2/255 turns #ffb020's blue (32)
into round(0.25) = 0 before any compositing happens. Same mechanism dashed a
static ground line drawn inside a tween: #5b6472 at alpha 1/255 premultiplies to
(0,0,0) and contributes nothing at all.

Measured across three inks at nine alphas: hue holds from about
`darkest_channel * alpha >= 1.2` and is visibly wrong below it -- and **alpha
1/255 is wrong for every ink, including near-white.** Which pass survives
therefore depends on the drawing, so the test is per-frame.

The fix sheds passes the ink cannot colour, always keeping the core. A
saturated ink gets a sharper exposure; a pale one keeps the full falloff.
Coarsening the exposure instead would have traded smoothness for colour on
every page, including the ones with no problem.

**Why every earlier measurement missed it:** they all used white or near-white
ink, whose channels are equal and high, and which is the one case where
premultiplied rounding cannot shift a hue. The test that would have caught it is
the one that varies the input along the axis the code is sensitive to -- here,
saturation -- rather than the axis that is convenient to draw.

## v244 -- Verified standalone is not verified in place

run275 failed on verify_hold with "Event loop is closed! Is Playwright already
stopped?". The new block called `br.new_page()`, but `br` belonged to a
sync_playwright() context that had exited long before.

The block had been checked standalone, in a script that opened its OWN
Playwright context -- an arrangement where that bug cannot exist. Passing in
isolation said nothing about passing in place, and it was taken as evidence for
both. A full sweep was spent finding out.

`run_harness.sh` takes a suite name as an argument, so checking one suite where
it actually lives costs about a minute. **Extracting code to test it changes the
thing being tested.** Run it where it will run.

## v245 -- An eraser takes away whatever is under it

The first pass at a drawn-in-Pad demo put a mistake-and-erase late in the
sequence, so the scrub went through finished artwork down to the paper and left
a white band across the face. Obvious once seen, and not obvious while writing
it: the mental model was "undo the wrong stroke", but an eraser is not undo.

Mistakes in a replay demo belong in the layer that is still on top -- during
construction, before anything is painted over them.

## v246 -- A warning is the wrong instrument when the safe state is "did not notice"

`current_user_id` without a CSRF verifier logged a warning, on the reasoning
that a bearer-token host does not need CSRF and should not be refused. The
reasoning was right and the mechanism was wrong. The failure mode is "any
third-party page can post as your logged-in user"; the warning went to a logger
the host may never have configured, at import time, in a stream nobody reads
during a deploy. The state you got by not noticing was the unsafe one.

It refuses now. **What makes refusing acceptable is that there is an explicit
declaration for the legitimate case** -- `csrf=False`, meaning "my
authentication is not cookie-based". Without that opt-out the refusal would be
punishing a correct configuration, which is how a hard error earns a reputation
for being wrong and gets worked around.

The rule generalises: a warning is right when the reader can act on it and the
default is safe. When the default is unsafe, the choice is refuse-with-an-
opt-out, not warn.

## v247 -- A number stated three times is stated zero times

Title and caption lengths lived in three places: `String(80)`/`String(300)` on
the columns, `[:80]`/`[:300]` truncating in the create endpoint, and
`maxlength="60"`/`"280"` in both editors. No two agreed, and an earlier session
had written a harness block headed "280 and 300 are different numbers ON
PURPOSE" -- pinning the drift as if it were a design.

It was not a design. A caption of 290 could not be typed into the editor but
posted fine; one of 350 came back **201** with fifty characters silently gone.

**OWNER, FLAGGED:** this reverses that earlier decision, and two assertions in
`verify_apiedges.py` were removed rather than adjusted, because what they
asserted was the drift. There is one constant per field in `core.py` now; the
columns are declared from it, the endpoint rejects with a 400 naming the limit,
and the templates render `maxlength` from it through the context processor.

The general form: when the same fact appears in N places, N-1 of them are
documentation of the other one, and only the one that can refuse is real.

## v248 -- A cap on bytes is not a cap on cost

Media validation proved the declared type matched the leading bytes and that the
base64 was under a size cap. Neither says anything about what decoding costs. A
66-byte PNG whose IHDR declares 30000x30000 passed everything, and every browser
that opened the post then allocated about 3.6 GB.

Bytes cannot be a proxy for decode cost, because the entire point of a
decompression bomb is that it is small. The dimensions are in the header of all
four accepted formats, so they read without a decoder and without a dependency.

Two choices inside it worth keeping. **An unparseable header ACCEPTS** -- a file
that will not parse does not decode either, and rejecting on "unparseable" turns
every rare corner of these formats into a 400 for no gain. And **the parser must
not become the attack** -- the JPEG segment walk is bounded by segment count and
byte offset, or a crafted file makes the scan itself the denial of service.

## v249 -- A maintenance function nothing can run is a maintenance plan, not a job

`sweep_orphans` reclaimed disk since v180 and was documented as the answer to
orphaned media. Nothing shipped could invoke it. Every deployment was left to
resolve its own app, find the store the host passed in, get a session, and get
the argument order right on a function whose third positional argument deletes
user data.

It was also unobservable: returning only the removed keys meant a run that
removed nothing looked identical whether there was nothing to reclaim, the
credentials were pointed at the wrong prefix, or the grace period was swallowing
everything. Every branch that DECLINES to delete is now counted separately,
which is what makes a zero interpretable.

And it was fragile: `delete_key` ran uncaught, so one object a bucket policy
refuses aborted the run and left every later orphan in place -- while the key
was already in the returned list, reporting a deletion that never happened.

The test for "is this operable" is not "does the function work". It is: can
someone schedule it, can they tell what it did, and does it survive one object
going wrong.

## v250 -- A number that goes stale is caught; a sentence that goes stale is not

`verify_docs.py` has guarded this project's volatile facts for many releases:
suite counts, file counts, assertion totals, tree hashes, version strings. Every
one of them is a NUMBER, and numbers are what it can compare.

It never occurred to anyone -- me included -- that the same rot happens to
prose, and prose is what people actually act on. `FOR-THE-REVIEWER.md` called
durable drafts and pointer identity "NOT deferrable prerequisites" two releases
after both shipped. `DESIGN-DIRECTION.md` stated the draft problem as current.
`START-HERE.md` said Pad's autosave "holds strokes but not media bytes" seven
hundred lines above its own paragraph explaining that the bytes go to IndexedDB.
A 3,328-assertion harness saw none of it.

**The cost was not embarrassment, it was a reviewer's time.** An outside review
of v224 read a stale docstring in `models.py` claiming the database limiter was
"NOT yet verified on PostgreSQL across processes" and filed a MEDIUM finding
asking for a test `verify_postgres.py` had been running since v211 -- four
gunicorn worker processes, twelve barrier-released requests, quota two. The same
docstring also denied that any advisory lock existed while `ratelimit.py` runs
`pg_advisory_xact_lock` on every reservation, so it UNDERSTATED a
security-relevant guarantee. Stale prose does not merely mislead a reader; it
spends the attention of the one person paid to find real problems.

The gate now pairs a capability with the artifact that PROVES it shipped and the
phrasings that would only appear if it had not. Two design choices are the
useful part. It scans SOURCE FILES as well as documents, because the finding
came from a docstring and code comments are read more literally than prose, not
less -- and that extension immediately found two more instances nobody had
reported. And its exemption list is a small CLOSED set of explicit markers, so a
changelog can still say what used to be true and adding an escape hatch is a
decision rather than a slide.

Stated in the code, because overclaiming here would be the same sin: it catches
denials it has PATTERNS for. A newly-invented stale sentence sails through
exactly as before.

## v251 -- Saying a fix is untested is not a substitute for testing it

The Air-brush beading fix shipped with an honest note in the reviewer document:
the mechanism was verified synthetically, the owner confirmed it by eye, and
**it is not pinned by an assertion**. That disclosure felt like diligence. The
v224 outside review ranked it as the second-most-important finding, and was
right to: an unpinned rendering fix is one refactor away from silently
returning, and the honesty in the document does nothing to stop that.

Why nothing else could see it: the STROKES ARE BYTE-IDENTICAL before and after
the repaint. It is not a geometry change, not a structural one, not a data one.
Only the pixels differ, and no suite here read pixels for this.

Two things about measuring it are worth keeping. **Read the alpha channel, not
the colour channels.** The canvas is transparent-backed -- the dark ground is
CSS behind it -- so `getImageData` returns STRAIGHT, un-premultiplied RGBA, and
a 22%-alpha white stroke reads r=255, a=56. The first draft measured red and
reported a spread of zero on a visibly correct stroke. That is the third time
this project has met premultiplied-vs-straight alpha in a new disguise. And
**exclude what is not ink**: a marquee paints a purple outline, and counting it
reported a spread of 138 for a repaint that was perfect.

The mutation is what makes the suite worth anything. It repaints through the raw
painters -- the pre-fix code path -- and REQUIRES the result to come back worse.
Composited mean alpha 51, raw 118. Without that, every other assertion could
pass on a canvas that never repainted at all.

## v252 -- "Sealed" is corruption detection, not provenance

`SHA256SUMS` lives inside the archive it authenticates, and so does the tree hash
in `RELEASE.md`. Anyone who can replace the archive can replace both. The v224
review said so and it is correct: the seal proves this archive is internally
consistent and the evidence describes this tree. It proves nothing about who
built it.

The honest fix available here is to publish the hash of the ZIP through a channel
that did not travel with the zip -- the git commit that seals each release. A
signed tag or a CI attestation would be stronger, and neither exists. The
documents now say which of those is true rather than letting "sealed" imply the
stronger one.

## v253 -- Evidence that does not name its own coverage invites a false finding

`RELEASE.md` recorded `skipped 1 (verify_mp4.py)` and stopped there. The v224
reviewer filed that as an open gap and recommended a CI lane with real H.264 --
which `.github/workflows/harness.yml` has run since v103, and which FAILS if the
suite merely skips. **The lane was shipping inside the archive under review.**

The finding was not careless; the evidence simply never pointed at the thing that
closed the gap, and a reviewer is not obliged to go looking for it. `RELEASE.md`
now prints, beside each skip, the CI job that covers it or the words NOT COVERED
-- generated from a table, never typed -- and `verify_docs.py` checks that each
named job really exists in the workflow and really invokes that suite, so the
sentence cannot outlive the lane.

## v254 -- A control belongs where its OBJECT is, not where its neighbours are

Flip's page bar held six controls. Five acted on a page; the sixth, "Move
artwork", moved the DRAWING. It had sat there since v124 for one reason: it was
added at the same time as the others, and a row already existed.

Nothing about it fitted. It takes a drag on the canvas, it has a mode, it
disables the strip while it runs, and it sits beside Select and Liquify in every
respect except where it was filed. It is now a tool in the tool shelf, which
cost a registry entry, a `setTool` branch, and one flagged ratchet edit in
`verify_tray.py` -- the roster there is deliberately exact so that a change to
what the product IS costs somebody a deliberate line.

**⚑ OWNER, FLAGGED:** that ratchet now reads six tools for Flip. Read it as a
control moving house, not as a new tool.

One bug fell out of the move and is worth recording, because it is the shape
these always take. `setTool` ended with `pad.style.cursor='none'` for the custom
brush cursor -- unconditional, and correct for every tool that existed when it
was written. Entering Artwork through `setTool` meant `setMoveMode` set the grab
cursor and then, four lines later in the same function, the old line wiped it:
the mode was live and the canvas did not say so. **Moving a feature into a
shared code path subjects it to every unconditional line already in that path.**

## v255 -- The badge was already drawn; it just was not a control

The page bar's ×hold button cycled a value that the filmstrip was ALREADY
displaying, on the tile it applied to. Two pieces of interface for one fact,
and the one that was better positioned was the one you could not press.

Making the badge the control removed the button. The only real design question
was what to do at hold = 1, where the badge did not render at all -- which is
why the button had to exist, since there was no way to START a hold from the
strip. It renders always now, and CSS hides the ×1 state unless the tile is
active, hovered or focused: exactly the rule the delete ✕ on the same tile
already followed. One idea about when per-tile controls exist, instead of two.

`focus-within` rather than `:hover` alone, because a control that appears only
under a pointer is a control keyboard users do not have.

The same reasoning retired the Paste button. A button in the add column could
say WHAT but not WHERE -- "after the current page" was a rule you had to know.
A dashed ghost tile standing in the gap the pages will fill says both at once,
and disappears with the clipboard.

## v256 -- Hover was spending the brand colour

`.pb:hover` tinted 16% violet and pulled its border to the accent. So did
`.addbtn:hover`. Six controls above a filmstrip, each lighting up in the one
colour the design direction wants spent almost nowhere, so that POST reads as
electricity.

Hover means "this is live", and a neutral lift says that. The accent is kept for
`:focus-visible`, where it is doing work no other signal does. The labels also
moved from `--text-primary`/600 to `--text-secondary`/500: chrome around
artwork should sit under it, and six full-contrast labels above a strip whose
job is to show DRAWINGS read as six things demanding attention.

Geometry was deliberately NOT touched -- 38px, 9px radius, and the invisible
44pt tap expander all stay. `.pb` is "labelled pill = named action" in the
documented shape language (DECISIONS #5) and its radius is not a tone question.

## v257 -- A refactor that moves the boundary is not a refactor

Flip's stylesheet carried eight `max-width` rules -- 359, 360, 392, 400, 440,
559, 560, 640 -- and styles.css had its own set. Not a responsive design: eight
patches, each correct on the day it was written, none of them agreeing about
where "small" begins. The measured cost is in this project's own review notes:
one pixel of resize takes Pad's toolbar from 398px to 565px, and 560-640px gets
the phone layout on a viewport with room to spare.

`lib/sizeclass.js` is the one decision those rules migrate onto. **What is worth
recording is the mistake made building it.**

The first version measured the ROOT ELEMENT rather than the viewport, on a good
argument: what every one of those rules actually wants to know is whether THIS
app has room, and Skribl is a blueprint a host mounts, possibly beside its own
chrome. But `getBoundingClientRect()` excludes the scrollbar, so a 641px viewport
measured ~626 and classified COMPACT where the media query it replaced said
regular. **The boundary moved by fifteen pixels inside a change announced as a
no-op.** The suite caught it because the no-op claim was the thing it was
pointed at hardest -- an assertion at 640 and another at 641, either side of one
pixel.

It measures `window.innerWidth` now, which is what the CSS `width` feature uses,
scrollbar included. Container-awareness is still the better long-run answer and
is recorded in the file as a BEHAVIOUR CHANGE to be taken deliberately once the
rules have moved, with the layout suite re-measured -- not slipped in on the way
past.

The general form, and this session has now produced it twice in two different
disguises: **when a change is sold as structural, the assertion that earns its
keep is the one that would fail if it were not.** Everything else in that suite
would have passed with the boundary in the wrong place.

## v258 -- Say what did NOT move

`verify_sizeclass.py` asserts that fourteen `max-width` queries REMAIN in
flip.css. That looks like an odd thing to test until you ask what the suite is
for: this step was announced as "replace the eight breakpoints" and delivered as
"add the class and migrate one as proof". Those are different sizes of work, and
the difference is exactly the kind that gets quietly forgotten between sessions.

An assertion that names the remaining work makes the narrowing permanent and
visible instead of conversational. It will fail, deliberately, when someone
finishes the migration -- and finishing it should cost a deliberate edit here,
the same way `verify_tray`'s exact tool roster does.

## v259 -- The host column is the case that decides how "small" is measured

**⚑ OWNER INPUT, and it reversed a decision made one release earlier.** The
social site reserves a COLUMN for Pad and Flip -- **around 510px, to be
confirmed by the owner.**

v257 chose to measure `window.innerWidth`, because the claim being made at the
time was that migrating a rule off `max-width: 640px` onto a size class was a
no-op, and innerWidth is what the CSS `width` feature uses. That was right for
that claim. It is wrong for the product.

A 510px column inside a 1400px window measures 1400 by the viewport and 510 by
the element. Viewport measurement therefore classifies the app REGULAR and lays
a persistent command row into a space that cannot hold one -- wrong in the
primary embedding, and wrong in the direction that breaks the layout rather than
the direction that wastes space. It measures the element now.

What that costs is asserted rather than discovered: `getBoundingClientRect()`
excludes the scrollbar, so a standalone window between about 641 and 655 now
classifies compact where a media query would say regular. Inside that band the
one migrated rule and the fourteen unmigrated queries disagree. **That is an
argument for finishing the migration, not for measuring the wrong thing in the
meantime.**

**STILL TO DISCUSS, once the owner confirms the number.** If the column really
is ~510px then Skribl inside the host is ALWAYS compact and never sees the
regular surface at all -- the persistent command row would exist only in the
standalone app. Two things follow, and both are the owner's call:

  * **Is 640 the right threshold for a column?** It was inherited from the
    existing breakpoints, which were written about phone viewports. A column has
    different arithmetic: no browser chrome, no address bar, and a known width.
  * **Is a second breakpoint worth having between 510 and 640?** A ~510 column
    is not a phone. It has a mouse, hover, and a keyboard, and it can afford
    controls a 360px phone cannot even if it cannot afford the full row. The
    compact/regular pair may want to become compact/column/regular -- which is
    a real design question and should not be answered by whoever next touches
    a stylesheet.

Nothing here should be built until the width is confirmed. `SkriblSize.COMPACT_MAX`
is one constant in one file precisely so that changing the answer is one edit.

## v260 -- Stage 4 shipped because its condition was met, not because it looked good

The compact surface drops the page bar for a ⋯ on the active tile. The design
note set one gate on this and it was not visual: **every operation must stay
reachable and announced**, because a filmstrip you can only operate by dragging
is a filmstrip some people cannot operate at all.

So the trigger is a real button with `aria-haspopup` on a tile in the tab order,
opening a `role="menu"` of real buttons; focus moves in on open, arrows walk it,
Escape returns focus to the trigger, and the items are no smaller than the `.pb`
buttons they replace. Each of those is an assertion, not a description. There is
also one proving the REGULAR surface was untouched -- **a change scoped to one
surface is only correct if it left the other alone**, and nothing else would
have caught it if stage 4 had quietly hidden the desktop row too.

The visible scope goes in `aria-label`, not `title`: `lib/tooltip.js` adopts
every `[title]` into `data-tip` and REMOVES the attribute so a styled tooltip can
replace the native one. A screen reader hears "Move these 3 pages left" while
the menu still reads "Move left".

## v261 -- Removing a surface makes the rules that styled it unreachable

Stage 4 hides the page bar on compact. Compact is every width at or below 640 --
which is every width the `.pb-tx` label-hiding rules applied to. **The bar is
therefore never icon-only any more, and those rules are dead.**

verify_hold had a whole section built on that premise: it ran at a 390px
viewport precisely because the labels were hidden there. After stage 4 that
section measured a bar inside a `display:none` ancestor, and `querySelector`
finds hidden markup perfectly well -- so most of its assertions kept PASSING,
vacuously, and only the one that asked about LAYOUT (`offsetParent`) noticed
anything had changed.

That is the failure mode this project keeps meeting from new angles: a test that
reads structure passes forever after the structure stops being rendered. The
section runs at a regular width now, asserts the compact half explicitly, and
says in a comment that the premise inverted rather than quietly reversing it.

The dead CSS is FLAGGED, not removed -- it goes with the rest of the breakpoint
migration, not piecemeal.

## v262 -- Removing a surface silently retires the assertions about it

Stage 4 hid the page bar on compact. Three suites then had assertions that no
longer meant anything, and only ONE of them failed.

`verify_tips` clicked `#pbLeft` at 390px and crashed on an invisible element --
loud, obvious, fixed in a minute. `verify_hold` measured the bar's glyphs at
390px and mostly kept PASSING, because `querySelector` finds hidden markup
perfectly well; only its one `offsetParent` assertion noticed. And `verify_move`
asserted at 393px that entering move mode "replaces the page bar, not adds to
it" -- which stayed green while proving nothing, because the bar was already
`display:none` before the mode started.

That last one is the sharpest version. Its own comment, four lines above, warns
that the assertion had previously passed for four versions against a visibly
broken surface "because it asked the DOM what it had been told, not what it
drew". It was rewritten to measure layout. **Measuring layout was not enough**:
once the element is unconditionally hidden, a layout assertion about it is
vacuous too. The claim needed a width where the bar exists, so it now has its
own page at 1100px, and the 393px section asserts the thing that is meaningful
there -- that the move bar appeared.

**The rule this arc adds: when a surface stops rendering, grep for every suite
that names it.** Not for the ones that fail -- the failures find themselves. For
the ones that keep passing.

Practically: `grep` the suites for the ids of anything removed, cross-referenced
against the viewport widths each file uses. Three suites named page-bar ids at
compact widths here; one crashed and two went quiet.

## v263 -- Adding a prefix to a selector is a specificity change first

Finishing the size-class migration meant putting `[data-size="compact"]` in
front of rules that already existed. That reads like a scoping change. It is
first of all a **specificity** change: `.flip-tools` is (0,1,0) and
`[data-size="compact"] .flip-tools` is (0,2,0), and every rule the original lost
to, the prefixed one now beats.

`flip.css` is exactly the file where that matters, and it knew it. Its own
comment at the max-640 block reads: *"This block is LATER IN THE FILE than the
max-560 and max-392 tiers above at equal specificity, so it wins on source order
-- which is why the row's phone gap, padding and group margins are declared here
and not up there with the widths. Moving them loses them silently; that is
exactly how the old max-380 tier's gap came to be dead code."*

So the ladder is held together by source order among rules that are all
(0,1,0). Prefixing the boundary rules lifts them out of that contest and they
win at every width. **Measured, not reasoned: the 320px tier's gap went 2px ->
3px** -- a phone regression, inside a change whose entire claim was "no-op".

The fix is `:where()`, which contributes zero specificity, so source order still
decides. The mutation is in `verify_sizeclass`: strip the `:where` and the 320px
assertion fails. That mutation is the point -- without it the `:where` looks
like a stylistic tic and the next person deletes it.

**The general rule: before prefixing an existing selector, ask what it currently
LOSES to.** If the answer is "rules at equal specificity, decided by order",
a prefix is a rewrite of the cascade and `:where()` is how you avoid it.

## v264 -- A progress counter is not an invariant

`verify_sizeclass` asserted `left > 0`: some `max-width` queries still exist.
The comment beside it was honest about why -- asserting their absence would fail
for the honest reason that the migration was incremental.

It was still the wrong assertion, and it stayed green through a real defect. It
is equally true of a migration 1/8 done and 7/8 done, so it measures **how far
along** the work is, and nobody was in doubt about that. What it could not see
is whether the queries left behind **disagreed** with the class -- and they did.
The class measured the element, the queries measured the viewport, and from 641
to 660 viewport px the page bar was hidden while the tool row kept its 44px
desktop sizing: the compact surface wearing the regular toolbar, shipped in
v227, with a passing suite.

The replacement is structural rather than a count: **no width query may sit at
or above `COMPACT_MAX`.** A query below the boundary can only refine the layout
inside compact; it cannot reach the edge to contradict the class. That holds at
1/8 done and at 8/8, it does not need editing as work proceeds, and it is false
exactly when the defect is present.

**The rule: when a migration is incremental, assert the INVARIANT that survives
every intermediate state, not the progress through them.** "Some remain" is a
status line. "None of the remainder can contradict the decision" is a test.

## v265 -- A remedy that always fires is not a remedy, it is the behaviour

`lib/pillfit.js` faded the autosave pill when it would cover a control. On a
desktop that condition is rare, so fading reads as a graceful exception. On a
phone the pill's fixed bottom-left corner overlaps the tool row at EVERY size --
the file's own header says so, in the sentence right above the fix -- so the
exception fired every single time and "Saved" was never once visible on a phone.

The file knew the collision was universal on phones and still chose a remedy
whose cost is proportional to how often it fires. Nobody measured the frequency,
because on the machine it was written on the answer was "almost never".

**Ask how often a fallback runs before choosing one.** A fallback that fires 1%
of the time can afford to be lossy. A fallback that fires 100% of the time on an
entire class of device IS the product's behaviour there, and it has to be as
good as the primary path -- or it has to be a different fallback. Lifting the
pill was available the whole time and costs nothing.

**And check what it composes with.** Warnings were exempt from fading, for a
good reason. Combine "reassurance always hidden on phones" with "warnings never
hidden" and the emergent behaviour is that a phone shows warnings and nothing
else -- a stuck amber pill on a healthy session. Neither rule was wrong. The
pair was, and no test covered the pair.

## v266 -- Do not paint a warning before the thing it warns about has happened

Flip's media autosave showed the amber "Saved without media" -- a pill that by
design NEVER fades, because a warning that fades claims it was resolved --
synchronously, before the IndexedDB write it describes had settled. Reaching
that code is the NORMAL path for saving media; the comments 80 lines up say so
outright.

Instrumented, the real sequence was:

    put:start bytes=4215866
    pill:saved-no-media        (+1ms)
    put:RESOLVED / pill:saved  (+13ms)

**13ms of a false alarm is not visible on the machine that writes the code**, and
that is the entire reason it shipped. On a phone spilling megabytes the gap is
long enough to see, and if the write is slow or fails the warning is permanent:
an amber durability alarm parked on a session that is completely fine.

The honest state for a pending write is "Saving…", which already exists and
already stays up. Amber should be reachable only from the failure handler.

**The rule: a state that means "something went wrong" may only be set by the
code that LEARNED something went wrong.** Setting it optimistically and
correcting it later inverts the cost -- the correction is the fast path on fast
hardware and the slow path exactly where the user is least able to tolerate it.

**And the test that missed it was checking the resting state.** A resting-state
assertion passes identically on the broken and the fixed build; only recording
the whole sequence could tell them apart. When a bug lives in an intermediate
state, assert the sequence.

## v267 -- Writing an attribute you observe is a loop, even when nothing changes

`pillfit.sync()` writes the pill's `class`; `pillfit` observes the pill's
`class`. `classList.remove()` sets the attribute even when the token was not
present, and setting an attribute fires a MutationObserver record even when the
serialized value is identical. So every unconditional write fed the observer,
which scheduled another animation frame, forever -- on an idle page, with the
pill hidden, doing nothing.

Measured on a phone viewport three seconds after everything settled: **133**
writes before the guard, **364** once lifting added two more per pass, **0**
after. It predates the v229 work; lifting doubled it, which is the only reason
it was noticed at all.

**Guard every write behind "would this change anything?"** when the writer and
the observer are the same component. It is not a micro-optimisation there; it
is the difference between converging and spinning. And a drawing app that keeps
a requestAnimationFrame loop alive while the user is doing nothing is spending
a phone battery to accomplish nothing.

## v268 -- A second route to an action orphans the first route's side effects

Shape has a kind picker. It opened from a click handler bound to
`#toolGroup .tool-btn` -- the tool SHELF -- and that was complete and correct
until v227 put a TRAY in front of the shelf.

After that, picking Shape from the tray called `setTool('shape')` through
`lib/toolshelf.js` and never touched the shelf's handler. The tool switched. The
picker did not open. Shape used whatever kind it already had, which for anyone
who had never happened to have Shape sitting on the shelf was `line`, forever.
It shipped in v227 and survived v228, v229 and v230 before a user said "shape is
not giving a choice, just gives you line".

**Nothing failed.** The action still worked; only its follow-on was missing, and
only on the new path. That is what made it invisible: no error, no dead control,
no wrong pixel -- just a dialog that never appeared, in a product where nobody
knew it was supposed to.

**The rule: when you add a second way to trigger an action, list every side
effect attached to the first way and move them to where the routes converge.**
Not "check the new path works" -- it did work. Ask what the OLD path did
BESIDES the action itself.

Here the convergence point already existed: `lib/toolshelf.js` calls the
surface's `setTool` for shelf and tray alike. The fix was three lines and the
diagnosis was the whole job.

And the test has to exercise the NEW route. The shelf route never broke;
asserting it proves nothing at all.

## v269 -- The union of rows is not the shape, and it perforates every slope

Fill's first version collapsed 6 pixel rows into one band and gave the band the
UNION of their extents. On a straight edge that is exact, which is why every
test and every desktop check passed. On a DIAGONAL the union is wider than the
narrow rows in it; the round-cap inset then pulls each run's ends back by half
its width; and where the region is narrow the run comes out shorter than its own
width and hits the short-run fallback, which draws a DOT.

So the first fill on the live demo drew a neat dotted line down the slope of a
triangle -- the fallback firing correctly, over and over, on geometry the banding
had misdescribed.

**Fixed-size decomposition of a shape is a guess about the shape.** Six rows is
right for a rectangle and wrong for everything else, and the wrongness does not
show up as an error, it shows up as an artefact somewhere nobody was looking.

Grouping rows by their ACTUAL extent removes the guess: a flat region is one run
however tall it is (48x47 box: 8 runs -> 1), a sloping edge is one run per row,
and the two cases need no separate handling. Cost follows the perimeter rather
than the area, which is both cheaper on ordinary shapes and exact on the hard
ones. **When a decomposition has a tuning constant, ask what the constant is
standing in for -- often the data already knows the answer.**

## v270 -- A tool's strength must not be a property of the device's sample rate

Blur's first version faded each touched point a little on every `pointermove`.
That reads as obviously correct and is obviously wrong the moment you ask how
many pointermoves there are: a 240Hz digitiser fires several times more often
than a 60Hz one for the same gesture, so the same swipe blurred several times
harder on a phone than on a laptop. v230's coalesced sampling had just raised
that rate ON PURPOSE, so the newer the hardware, the worse it got.

Measured: one short swipe took `#ffffff` to `rgb(87,89,92)`.

**Saturating the accumulation was the obvious repair and it was not enough.** A
cap bounds the maximum; it does not make a 4-event sweep land where a 40-event
sweep lands, because neither has reached the cap. The fix is to accrue against
the physical quantity the tool actually deposits along -- **distance travelled**
-- which is the same number however often the OS sampled the finger. 117/255
apart before, 6/255 after, and the residual is arithmetic: a falloff integrated
from 4 samples cannot equal one integrated from 40.

**The rule: when an effect accumulates over a gesture, accrue it against
distance or time, never against event count.** Event count is a property of the
hardware and the browser's scheduling, not of what the user did.

And the assertion that catches this cannot be a screenshot or a "did it blur"
check -- both pass. It has to run the same gesture at two sample rates and
compare, which is a strange-looking test until you know why it exists.

## v271 -- Look for what the format already honours before declaring it impossible

Blur looked unbuildable. The format is points; you cannot blur a polyline by
moving its points; there is no raster layer; adding one is a format change the
player must honour and therefore the owner's call, not a tool's.

That reasoning was sound and the conclusion was wrong, because of one detail in
`paintStatic()`: a stroke whose FIRST point is opaque gets painted by
`paintSeg` with **each point's own colour and own size**. Per-point colour is
already honoured, already replayed by the player, already in every saved file.
Blur is then just "fade this point toward the ground and widen it" -- entirely
sayable, no format change, no player change.

**Before concluding a feature needs a format change, enumerate what the RENDERER
already reads per point.** The format is not what the schema says; it is what
the paint path actually honours, and those can differ by more than one feature's
worth.

The corollary matters too: the obvious route -- per-point ALPHA -- genuinely is
not honoured, because `paintStatic` takes alpha from the segment's first point.
Two neighbouring fields, one usable and one not, and only reading the paint path
tells you which is which.

## v272 -- Test the renderer, not the plan

`verify_fill` had eighteen assertions and every one of them was about the shape
of the RUNS: one run per row on a slope, bounded height, every row covered
exactly once, two points per run. All eighteen passed on a build whose fills
visibly had holes in them, and the same bug got reported twice.

They passed because none of them knew that `drawLine` paints a STADIUM. Round
caps curve inward toward the top and bottom of a thick line, so a run's coverage
is not the rectangle its coordinates describe. The plan was correct and the paint
was not, and no amount of checking the plan could see it.

The assertion that found it rasterises the runs onto a canvas exactly as flip.js
draws them, then counts mask pixels the paint missed. It failed on its first run
-- 52 of 7845 -- and that is how the second half of the fix got found rather
than shipped a third time.

**When a component hands its output to a renderer, at least one test has to go
through the renderer.** Geometry tests are cheaper, they localise failures
better, and they cannot see anything the drawing API does on its own.

## v273 -- Prefer bleed to gaps

Fill's runs were inset by half their lineWidth so round caps would not paint past
the region's edge. That is careful, correct about the line's centre row, and
wrong at every other row of a thick line -- which is where the bare corners came
from.

Drawn to full extent instead, the cap bulges OUTWARD: every pixel of the region
is covered and the cost is a couple of pixels of bleed sideways, underneath a
boundary line already wider than that.

**Between an edge that stops short and one that runs over, the one that runs over
is the one nobody reports.** A gap shows as a hole against the ground; two pixels
of overlap disappear under the line that was already there. When a rendering
tolerance has to go one way, take the direction whose failure mode is invisible.

## v274 -- A promise with no timeout is a state machine with no exit

`SkriblDraftStore.put()` was awaited with a .then and a .catch and no deadline.
IndexedDB on iOS Safari can accept a multi-megabyte write and then settle
NEITHER way, so `_mediaSpillState` stayed 'saving' for the rest of the session
and the pill sat on "Saving..." forever. Worse, every subsequent save re-entered
the same branch and re-reported 'saving', so the stuck state was self-renewing.

Two handlers look like complete coverage and are not: success and failure are
not the only outcomes of an async call to something outside your process. The
third is SILENCE, and it has to be handled explicitly or it becomes a state the
UI can enter and never leave.

**Anything that can hang needs a deadline, and the deadline needs an opinion.**
Here the opinion is that bytes which have not landed in twelve seconds are lost,
because that is what a reload will find. A late resolve is then ignored on
purpose: the user has already been told the truth, and flipping the pill back to
green would un-tell it.

## v275 -- A test whose fixture is too easy is a test that passes on the bug

Two assertions were written for the fill's fringe gap and BOTH were vacuous.

The first drew a BOX. Axis-aligned edges barely anti-alias, so there was no
fringe for the fill to miss, and the assertion passed on a build with GROW set
to zero -- the exact defect it was written to catch. The second counted holes in
the shape's INTERIOR, shrunk by 18%, which excluded precisely the edge band
where the artefact lives.

Neither was a wrong assertion. Both were the right assertion pointed at a
fixture that could not exhibit the failure.

**Mutation testing is what caught it, and it is the only thing that could have.**
The assertions passed on the good build and on the broken one, so nothing about
running them told you anything. A test's fixture has to be able to FAIL, and the
cheapest way to know is to break the code and watch.

**Practically: when a bug is reported on a curve, test a curve.** The reproduction
the user gave is the fixture; simplifying it to a rectangle for convenience
throws away the property that produced the bug.

## v276 -- A point is a payload field, not a scratchpad

Smudge needed per-point state: how far this point has been smeared, and what its
colour and size were before the drag started. The obvious place is a property on
the point.

Points are serialised wholesale into every autosaved draft and every shared
Skribl, and copied by Object.assign into the undo snapshot. A scratch field
named `_sm` would have ridden into all of it and arrived at the server's
validator, on every stroke the user ever smudged.

It lives in a WeakMap keyed by the point object instead -- which also happens to
be more correct: liquifySubdivide INSERTS points mid-drag, so an index captured
before a split refers to a different point after it. Keying off identity
survives that; keying off position does not.

**Anything shaped like a record that leaves the process needs its scratch state
kept somewhere else,** and the assertion is cheap: no key on a point may begin
with an underscore.

## v277 -- A status is about THIS operation, not about the history

Flip's autosave pill reported "Saved without media" whenever a pending media
record existed. Reaching that branch means there is no photo and no track on the
page at all: the save omitted NOTHING. The record is a memo about a past loss,
kept so the user can re-add the same image with its settings.

Conflating the two put a permanent amber warning on a drawing with no media in
it. It was permanent because three separate things lined up: the record
round-trips through the draft, the control that clears it is 0x0 until a drawer
is opened, and warnings deliberately never fade. A warning with no reachable
resolution.

**The cost is not the wrong word on a pill; it is the colour.** Amber has to
carry a real "your bytes are gone", and it can only do that if it is rare and
true. A status that fires on history teaches people to ignore it, and then the
one that matters arrives in a colour they have learned means nothing.

**The rule: a status describes the operation that just ran.** If the state is
about something that happened earlier, it belongs to whatever offers the remedy
-- here, the re-add card -- not to the indicator for the current write.

## v278 -- A shared test helper is not surface-agnostic just because it is shared

A new Flip assertion used `DRAW_STROKE`, the helper the Pad sections use. It
targets `#canvas`, which is Pad's element; Flip draws on `#pad`. So on Flip it
drew nothing, scheduled no save, and the assertion read whatever the pill
happened to be showing.

It did not error. It reported "Saving..." and failed for a reason that looked
plausible -- a save still in flight -- which cost a round of chasing the wrong
thing.

**A helper lifted to the top of a file reads as applying to the whole file.**
When two surfaces share a suite, anything that touches the DOM has to say which
surface it is for, or be parameterised by it. The tell is an assertion that fails
with a value that is merely UNEXPECTED rather than wrong.

## v279 -- Ask what the structure survives, not just what it looks like

A fill and a line look identical once drawn: white ink on the page. They behave
completely differently the moment something drags them, because a line is ONE
stroke and a fill is a stack of thin horizontal ones. Smudge moves neighbouring
runs by different amounts -- that is what a falloff IS -- so the stack fans
apart and the ground shows through as a comb.

The number is small and decides everything: runs 0.9px apart, the falloff
varying 4.7% across that spacing, so separation grows at ~4.3% of the drag. With
3.1px of overlap the fill survives 72px of dragging and no further.

**A representation is not finished when it renders correctly.** It has to be
asked what happens when the OTHER tools touch it. Fill was measured against
"does it cover the region", and it did, perfectly -- and it was still the wrong
shape for a canvas where things get pulled around afterwards.

The follow-on is that the mitigation has a ceiling worth stating plainly rather
than tuning toward: surviving a 200px pull needs 8px of overlap, and the fill
would spill past its own boundary. Some limits are not bugs to be fixed but
consequences to be named, so the next person does not spend a day rediscovering
them.

## v280 -- Pin the constant that does not look load-bearing

`BLEED` reads like a rounding guard: draw each run a pixel taller so adjacent
ones meet instead of leaving a seam. It is also, and much more importantly, the
entire budget a filled region has for being smudged, liquified or moved.

Nothing about the name or the value says that. A later reader doing honest
cleanup -- "the runs already tile exactly, why is this wider than the group?" --
would halve the drag distance a fill survives, and see nothing wrong in any
screenshot they took.

So the assertion states the consequence, not the value: runs must be drawn
wider than their group, and the failure message carries the measurement (3.1px
of slack combs after ~72px, 5.1px after ~119px).

**When a constant's obvious purpose is not its important one, the test is where
you say so** -- a comment is read by someone already editing the line, and a
test is read by someone who just broke it.

## v281 -- A test that depends on list order is a test waiting to change meaning

`verify_tools` checked "Shift gives a circle" on Flip directly after a loop over
the shape kinds, with no selection of its own. It worked because 'ellipse'
happened to be last in KINDS. Adding a fourth kind made the loop end on 'poly',
and the check started drawing a shifted POLYGON -- which has a real bounding
box, so it failed with plausible-looking numbers rather than an error.

That is the expensive shape of this bug: the failure looked like a geometry
regression in the code under test, not like a precondition that had gone stale.
Pad's equivalent assertion selected 'ellipse' explicitly and was untouched.

**State a test's preconditions rather than inheriting them.** Anything a check
depends on -- the current tool, the current kind, the current page -- has to be
set by that check, even when the line above happens to leave it right. The cost
is one line; the alternative is a failure that sends someone into the wrong file.

## v282 -- Clamp in the geometry, not on the control

The corner-rounding slider can be asked for more radius than an edge can give,
which folds the shape through itself. The obvious guard is a `max` on the range
input -- and it cannot work, because the limit is half the SHORTEST EDGE of a
shape the user has not drawn yet. It differs with every kind, every drag size
and every aspect ratio.

So the clamp lives where the shape is built. Run the slider to its end and
rounding simply stops increasing, which is what a control at its limit should
do, and there is no state where a legal input produces an illegal shape.

**When a control's valid range depends on data the control cannot see, the
validation belongs to the thing that CAN see it.** A widget-level max is a
promise about a relationship it has no access to, and it will be wrong in
exactly the cases nobody tried.

## v283 -- Derive a mode's UI from the mode, do not toggle it at the call site

The stamp shelf has to be on screen for as long as the Stamp tool is selected:
without an armed stamp the tool does nothing, so "which stamp is loaded" is not
decoration, it is the tool's only state.

The shape picker, one control along, is the version that toggles. It opens in
the tool-shelf config, which is where the shelf button and the overflow tray
both converge -- and that was already a repair. The picker originally opened
from a click handler bound to the shelf, which was complete until v227 put a
tray in front of it; after that, choosing Shape from the tray never opened the
picker and Shape silently stayed on whatever kind it had. That reached the live
demo as "shape is not giving a choice, just gives you line".

Writing stamps the same way passed every assertion I wrote by hand and failed
the first one the suite ran, because the suite reached the tool by a route the
config does not sit on. Two routes had become three.

So the shelf's visibility is DERIVED, in `setTool()`, from which tool is active:
`hidden = (flipTool !== 'stamp')`. There is no route that can forget it, because
there is nothing to remember. The only thing left at the call site is the
deliberate override -- tapping the tool button while its own tool is already
active puts the shelf away -- and that is applied after the derivation rather
than instead of it.

**A UI that belongs to a mode should be computed from the mode, not switched on
by whoever happened to enter it.** Every new entry point is another place to
forget, and the forgetting is silent: the feature does not break, it just is not
there for the people who arrived the other way.

## v284 -- A shelf that only grows needs a byte budget, not a slot count

localStorage is ONE allowance, about 5 MB, for the whole origin. v231 has the
scar: Flip's draft grew to 2.7 MB of it and the Pad's autosave -- an unrelated
feature on an unrelated page -- started failing, with nothing in either feature
mentioning the other.

A stamp shelf is that trap by construction, because it only ever grows: every
stamp you save stays until you delete it. Capping the number of slots is the
obvious defence and it is a proxy for the thing that matters and a bad one --
one traced outline is worth fifty doodles. So the cap is on BYTES, the encoding
is compact enough that the budget buys a useful number of stamps, and the shelf
lives in its own key so a shelf that will not write can never take the drawing
down with it.

It also **refuses rather than evicting**. Dropping the oldest stamp to fit a new
one is the friendlier-looking design and it is the amber-pill failure over
again: the user's work disappearing with no event they can connect it to. A
stamp is something they deliberately made. Losing one has to be their decision,
so a full shelf says it is full.

**When a store only grows, decide what happens at the ceiling before you build
it, and measure the ceiling in the unit the resource is actually rationed in.**

## v285 -- The fixture is the assertion; two mutations proved it twice in one file

Every assertion in `verify_stamps.py` passed on the first build. Two of them
also passed on a deliberately broken one.

The undo contract -- one tap is one undo, however many stroke groups the
placement produced -- was tested with a stamp made from a SINGLE stroke. On a
build that recorded `groups: 1` instead of the real count, one group and the
real count are the same number, so the assertion agreed with the bug.

The no-op contract -- a tap with nothing armed places nothing -- was tested
against an EMPTY shelf. On a build that helpfully armed the first slot for you,
there was no first slot to arm.

Neither is a missing assertion. Both are assertions whose fixture could not tell
the two answers apart. The fixes are a two-stroke drawing and a shelf that has a
stamp on it, and the reasoning is now written into the fixture helper rather than
next to the check, because that is where the next person will change it.

**An assertion is only as strong as the case it runs on, and the weakest fixture
is the one where the right answer and the wrong answer coincide.** Mutating the
code is the only way to find those; reading the test will not do it, because the
test reads correctly.

## v286 -- A warning is only intolerable when it has nowhere to go

`verify_amber.py` was FAILING on `main`, on one assertion, and I caused it. It
passed at v234 and my v235 change broke it -- confirmed by checking out v234's
`flip.js` and watching the assertion go green again. It went unnoticed for three
merges because each was reviewed against the suites its own diff touched.

**What v235 was answering.** A live report: the amber "Saved without media" pill
sitting permanently on a drawing, coming back on every save, with no way to
clear it. v235 made the save status describe only the write it belongs to, so
the no-media path reports plain "Saved".

**What that cost.** Reload a session whose track genuinely never saved and the
pill says "Saved" with the track gone. And there is nothing in the code to tell
the two cases apart: in the live report and in the failing test the draft is
IDENTICAL -- `mediaOmitted` set, a pending record restored, no bytes. Either the
warning is shown or the loss is silent.

**So the fix was never about which state to show.** What made the old amber
intolerable was not that it was wrong. It was that it went nowhere: the pill
said media was missing, and the only controls that could do anything -- Re-add
and Dismiss, on the pending card -- lived inside a shut drawer, measuring 0x0
until something opened it. Nothing on screen pointed there. v235 removed the
warning instead of the dead end.

The amber is back and the pill is now the route: it reads "Media missing -- tap
to re-add", it is a control while and only while there is something to re-add,
and tapping it opens the drawer holding the card. Dismissing clears the record,
which schedules a save, which reports plain "Saved" -- the warning ends because
the situation did. Two wordings, because an amber raised when the media is still
LOADED (no store to spill to) has nothing to re-add and must not promise
otherwise.

**A true warning the user cannot act on trains them to ignore the colour.** The
repair for that is a route, not silence. Deleting the warning makes the screen
calmer and the product worse, and it is the easier change, which is why it is
the one that gets made.

Three things this needed that were invisible from the JS:

* `pointer-events: none` on the base pill. Correct -- a floating status must not
  eat a tap meant for the control beneath it -- and it meant a click listener
  did nothing at all, because the event never reached the element.
* `transform` collides. `pillfit` LIFTS the pill with `translateY` (209px on a
  390px phone); an `:active { transform: scale(.97) }` in a later stylesheet
  REPLACES that lift, so pressing the pill dropped it 209px out from under the
  finger pressing it. Found by a click that timed out, which is the same thing a
  thumb would have experienced.
* `typeof x !== 'undefined'` does not shield a `let` in its temporal dead zone;
  it throws the identical ReferenceError. The pending records had to move up to
  the media state, not acquire a guard that does not guard.

## v287 -- A mutation caught is not a mutation reported

Six mutations of the fix above were all caught. Four of them were caught as
`ERROR -- crashed before reporting`, with no assertion named.

The cause is that Playwright waits for actionability before clicking. Against a
pill still carrying `pointer-events: none`, or a Dismiss button sitting 0x0 in a
drawer that never opened, `page.click` does not fail fast -- it blocks for the
full default timeout and raises. Both of those are exactly the states the
section is testing for, so the defect under test was also the thing destroying
the report of it.

A crash and a failure are not the same signal. A crash reads as an
infrastructure problem, it names nothing, and this project has a section in
START-HERE about suites whose failure could not travel through the reporting
channel. The clicks now go through one guarded helper with a short timeout that
turns "was never actionable" into an ordinary FAIL with a sentence.

**When the thing you are testing for is also a thing that can wedge your test
harness, the guard against wedging IS the assertion.** Verify a suite by
mutation, then look at HOW it failed, not just that it did.


## v288 -- Measure the thing the eye is responding to, not the thing that is easy to measure

"Fill is a weak icon" turned out to be measurable. Rasterise every tray glyph and
read its ink bounding box off the alpha channel: Fill filled 15.0x16.3 of its 24
box where every other tool sat near 19x18. It was the smallest thing in the tray,
and it was a hollow diamond whose handle was a 3px stub, so at tray size it read
as a tilted square with a dot.

The measurement had to be of the RENDERED icon. Path coordinates say nothing
about how much of the box a drawing occupies -- stroke width, caps, joins and
fills all add ink outside the geometry, and two icons with identical viewBoxes
can differ by a third in apparent size. Reading the SVG source would have found
nothing.

**Two numbers were available and only one of them was the answer.** Ink EXTENT
tracked the complaint exactly. Ink COVERAGE -- the share of the box painted --
did not, and following it did damage: Stamps was "improved" from 24.3% to 19.7%
coverage and came out visibly worse, because the weight being removed was a solid
base bar holding the icon together. Two glyphs at the same coverage look nothing
alike when one is a thin outline over a wide area and the other is a small solid
mass. The suite reports coverage and refuses to assert it.

## v289 -- An exemption needs a sentence, or the band eats the drawing

Liquify is the flattest icon in the tray by a wide margin: 20 wide, 13.5 tall,
against an ~18 norm. By the band it is the worst offender in the set. It is also
correct -- it is a smear, and a smear is wide and low.

I redrew it to fill the box's height. The number improved. The icon became a
caret with a detached curl, and I only found that by rendering it next to the old
one and looking. The metric was satisfied and the drawing was worse, so the
drawing won and the redraw was reverted.

Which leaves a suite whose band Liquify fails. The fix is not to widen the band
until it passes -- that would re-admit the 15x16 Fill this all started with. It
is exempt BY NAME, in a dict whose values are the REASON, printed in the
assertion's detail. The next person to run this finds "a smear is wide and low;
the tall redraw read as a caret" instead of a red line inviting them to make the
same change I did.

**A numeric band over a design decision will eventually be satisfied by someone
who cannot see the design.** Carry the reason in the exemption, in the output,
where it will be read at the moment it is needed.

## v290 -- At 24px only the silhouette survives, so judge at 24px

The first repair of the Fill icon grew it from 15.0x16.3 to 19.8x18.8 -- into the
band, measurably fixed -- and the owner said "there's got to be a better one".
They were right. The size was never the whole complaint. The handle was a 3px
stub, and a stub does not become a handle by being scaled.

Fifteen candidates were drawn and rendered side by side at 4x AND at the 24px
the tray actually uses. The 4x row is nearly useless for deciding: a tipped can
with an open elliptical rim, a bucket pouring into a pool, a region with a drop
falling into it all read beautifully at 4x and turned to mush at 24px. The pour
became a desk lamp. The open rim became a rolling pin.

What survives 24px is the SILHOUETTE and nothing else. Which is why the winner
kept the original diamond-can outline -- already the strongest small shape in the
set -- and spent every change on the two things that were not legible: the stub
became a quarter-arc handle, and the drip grew until it stayed a separate shape
instead of merging into the can's corner.

Solid-bodied variants read better still in isolation, and at ~40% ink coverage
were twice the weight of anything else in the tray. An icon is not judged alone;
it is judged in the row it sits in.

**Render every candidate at the size it will actually be used, and decide there.
A comparison at 4x is a comparison of drawings, not of icons.**

## v291 -- A shared icon spec on paper is not a shared scale in practice

The tool glyphs are 24x24, 2px stroke, round caps and joins. That is Lucide's
spec exactly, so dropping two Lucide icons in should have been a copy and paste.
Measured, it was not: Lucide draws to the full box and `paint-bucket` and `stamp`
came in at 22.0-22.2 units of ink against a set that sits near 19. Fifteen per
cent larger, and correspondingly heavier, than the eight glyphs beside them.

Nothing in either SVG says so. Same viewBox, same stroke width, same joins --
and a visibly different size on screen, because "how much of the box the drawing
occupies" is not a property either file declares. It is only visible if you
rasterise and measure, which is the same lesson as v288 arriving from a new
direction.

Each is now scaled 0.88 about the box centre with its authored stroke raised to
2.27, so the RENDERED stroke lands back on 2px. The drawing is Lucide's,
untouched; only its size in our box is ours, and the attribution says so rather
than claiming the icons are unmodified.

**Matching a spec is not the same as matching a look. Verify the rendering, not
the declaration.**

## v292 -- Two exemptions is a smell, so make the exemption cost something

`verify_icons.py` now excuses Liquify from the height floor (a smear is wide and
low) and Stamps from the width floor (a rubber stamp is tall and narrow; Lucide's
is 18:22 and no uniform scale satisfies both the width floor and the height
ceiling). Two exemptions in a ten-icon band, the second added to admit a change
I was making, is exactly the shape of a guard being quietly dismantled.

So the exemption was given a price: an area floor that applies to every icon,
exempt or not. A glyph excused on one axis still has to occupy a comparable
amount of the box. Mutation-tested three ways -- the original weak Fill still
fails, an exempted icon shrunk to nothing still fails, and raw unscaled Lucide
still fails.

The margin is thin and is written down rather than rounded to something tidier:
Liquify at 270 is the smallest thing that must pass, the original Fill was 245.
Which is why the comment says outright that this is a BACKSTOP and not the
guard -- the per-axis floors do the real work, and that Fill failed both of them
too.

**When you widen a rule to admit your own change, add a rule that the change
still has to pass.** An exemption that costs nothing is a deletion with extra
steps.

## v293 -- A mockup is not a bill of materials

The icon options came as two images: a set of tray mockups and a grid of forty
named Lucide icons with seven recommended picks. The names were checkable, so
they got checked against lucide-static 1.37.0.

Fourteen of the forty do not exist. `pen-nib`, `hand-move`, `move-2`,
`paint-bucket-icon`, `square-fill`, `circle-fill`, `bucket`, `swirl`,
`wavy-lines`, `ripple`, `distort`, `blur`, `seal`, `picture-frame` -- including
four of the seven RECOMMENDED picks. And the glyph pictured for Liquify was a
finger with ripples while the name under it was `waves`, which in Lucide is three
wavy lines: the picture and the name were different icons.

The two that mattered were real, and both shipped. But a shopping list that is a
third fiction would have produced a pile of 404s and a quiet substitution of
whatever was nearest.

**Check names against the package, not the mockup.** It took one `npm pack` and
a loop.

## v294 -- The shape of the thing constrains the shape of the rule

Fill became a drop, on the owner's call, and a drop does not fit a band derived
from ten square-ish icons. A teardrop that reads as a teardrop is roughly 17:22 --
a sharp point over a round body -- against a band that wants at least 17.5 wide
and at most 21 tall.

The first attempt widened it to fit. The apex blunted, and it came out looking
like a peach. The band was satisfied and the icon was no longer a drop.

What fixed it was inverting the order: the APEX is the icon, so the control
points were set first to keep the tangent leaving the point steep, and the
proportions were tuned around that until 18.5x20.8 fell out. Inside the band
without touching the band, and still unmistakably a drop.

That mattered because the alternative was a third named exemption, three weeks
into a suite with two. Two exemptions describe a set with two genuinely
non-square members. Three, each added to admit the change being made at the time,
describes a rule that no longer constrains anything.

**When a design constraint and a numeric rule collide, try re-deriving the design
from its essential feature before touching the rule.** The rule is often fine and
the drawing was simply built in the wrong order.

## v295 -- Blur should look blurry

The Blur glyph was three concentric outlined rings, which reads as a target. The
reference sets proposed a dashed circle, which reads as a selection marquee.
Neither is blurry.

It is now a filled core inside progressively larger, fainter filled halos --
which is what defocus actually looks like, and which survives 24px precisely
because it has no internal edges to lose. It is the only soft form in a tray of
line drawings, and that is not an inconsistency to tidy away: it is the only tool
whose entire subject is softness.

**An icon for a visual effect should exhibit the effect, not diagram it.**
