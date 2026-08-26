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
Without it, any page on the internet can post as the logged-in user.

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
