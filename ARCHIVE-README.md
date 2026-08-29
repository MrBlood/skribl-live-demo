# What this archive is

**Source version: `SKRIBL_VERSION = "v232"` (skribl/core.py).**

**The release evidence in this archive is THIS tree's.**
`harness/RELEASE.md` and `harness/LAST-RUN.txt` are generated from a full
aggregate run executed against the tree in this archive. **Read the totals
there, not here** — the result, the assertion count, the suites reporting and
anything skipped are all stated in `harness/RELEASE.md`, and restating them in
this paragraph is how a number goes stale one release later while still
sounding authoritative. (`verify_mp4.py` skips in any build container without
an H.264 profile; a skipped suite contributes zero assertions and is not
evidence of coverage.) The tree hash in `RELEASE.md` is computed, and every
file here is listed in `SHA256SUMS`, so both claims are checkable without
trusting this sentence. What changed and why: `V227-CHANGES.md`.

**WHAT "SEALED" DOES NOT MEAN.** It means this archive is internally consistent:
every file matches the manifest, and the manifest matches the tree the evidence
was produced from. It is **not** provenance. `SHA256SUMS` lives inside the
archive it authenticates, and so does `harness/RELEASE.md`'s tree hash — anyone
who can replace the archive can replace both. The seal detects corruption and
accidental substitution; it does not prove who built this or that it is the
build someone approved. (v224 outside review, R5.)

If you need provenance, take the hash of the **zip** from a channel that did not
travel with the zip. This project publishes it in the git commit that seals each
release, on the branch the archive was built from — compare
`sha256sum skribl-v232-sealed.zip` against the value in that commit message. A
signed tag or a CI attestation would be stronger and neither exists yet; the
git-history channel is what is actually here, and saying so beats implying more.

Read that line first. This archive's contents are built on the **v131** client
code — `app.js`, `flip.js`, `styles.css` and `flip.css` are v131's, with the
integration edits listed below plus the two v142 features. If you have a later
line of work (a v13x with newer editor/Flip/CSS changes), **this archive does
not contain it**, and
merging means bringing those four files here rather than the reverse.

The filename is DERIVED from `SKRIBL_VERSION`, not typed alongside it. Earlier
deliveries were named for a version the code inside did not declare — v132/v133/
v134 archives containing v131, and an archive named v137 containing v131 — which
is the same class of error as the editor's hardcoded version drifting nine
releases, the README claiming v118 while the code said v131, and SHA256SUMS
claiming 50 files while covering 82. A version in the name is fine; a version in
the name that nothing checks is not. `verify_docs.py` now fails if the README's
stated version disagrees with the constant.

## What changed here, versus v131

**The server was repackaged as a Flask blueprint.** `app.py` went from 1,202
lines to 116 and now does only host work. Everything else moved into `skribl/`:

    skribl/__init__.py    create_blueprint() / init_skribl() — the contract
    skribl/routes.py      the routes, incl. the feed and media endpoints
    skribl/models.py      plain SQLAlchemy, injected session, visibility column
    skribl/ratelimit.py   incl. the concurrency fix described below
    skribl/validation.py  moved verbatim from app.py
    skribl/security.py    CSP (blueprint-scoped) + embed origins + CSRF
    skribl/storage.py     media backends: inline (default) / local / S3 hook
    skribl/core.py        version, OG defaults, id validation, env parsing
    skribl/migrations/    Alembic, scoped to Skribl's tables only

**Behavioural changes:**

* Rate limiting no longer admits ZERO under concurrency. Reservation was
  INSERT → COMMIT → COUNT → withdraw; twelve simultaneous posts against a quota
  of two all committed before any count ran, so every request withdrew. SQLite
  hid this by serialising writes. Fixed with a per-identity advisory lock.
* `GET /api/skribls` — feed listing, keyset cursor, payloads excluded.
* `visibility` on posts: public / unlisted / private. **New posts default to
  `unlisted`, and the migration backfills existing posts as `unlisted`.** A
  client must ask for `public` explicitly to appear in a feed. See DECISIONS.
* CSRF seam, opt-in via `SKRIBL_CSRF_PROTECT=1`.
* Media can live outside the database. Default is still `inline` (v131
  behaviour); `SKRIBL_MEDIA_BACKEND=local` externalises it.

**Client edits — the six integration edits.** Re-apply these if you merge newer
client files:

    flip.js    window.SKRIBL_API_BASE instead of a hardcoded '/api/skribls'
    flip.js    window.SKRIBL_PLAYER_BASE instead of a hardcoded '/s/'
    flip.js    mediaToArrayBuffer() — handles data URLs AND external URLs
    app.js     skriblPostHeaders() — sends the CSRF header when present
    app.js     removed the '/api/skribls' literal fallback
    templates  skribl_asset() instead of url_for('skribl.static', …)

`harness/verify_seam.py` fails loudly if any of these is missed.

**Client changes added in v142.** These are features, not integration seams, so
they are listed separately — a merge should take them or leave them as a unit,
not re-apply them line by line:

    flip.html  a compose step (title, caption, counter) before the share result
    flip.js    buildSharePayload() sends the typed title/caption. It sent
               title:'Flip animation' and no caption, so every Flip post
               reached the platform with the same meaningless title
    flip.css   the compose/result panes; scoped :not([hidden]) so an explicit
               display does not defeat the hidden attribute
    flip.js    sizeFor() — stylus pressure scales the per-point size
    app.js     pressureSize() — the same, via Touch.force

`harness/verify_flipmeta.py` (24) and `harness/verify_pressure.py` (27) cover
these, both driving a real browser.

**Client changes added in v143 — the export sheet.**

    _skribl_export.html   Size/Pages labels above their controls; a scope note
                          ("Applies to video and GIF" — PNG honours neither);
                          "to" instead of a bare en-dash; GIF background reads
                          Solid | Transparent, data-gif-bg values UNCHANGED
    flip.css              the rules for .export-optlbl, .export-num,
                          .export-dash, .export-optblock, .export-optnote and
                          .export-size-seg — see below
    flip.js               two readouts instead of one combined string

**Five export classes had no CSS anywhere in the tree.** `.export-opt-row`,
`.export-optlbl`, `.export-num`, `.export-dash` and `.export-rangenote` were in
the markup and in no stylesheet, so the browser fell back to defaults: bare
number spinners, a raw en-dash, and a flex row that wrapped and left the readout
"62 of 62 · 640×460" orphaned on a line of its own. A sixth, `.export-size-seg`,
was a dead hook — the control is styled by `.seg` and the JS binds the id.

Nothing caught this because nothing could: the harness asserted behaviour and
source seams, and a class present in markup and absent from CSS is neither.
`verify_exportui.py` now sweeps EVERY class in the export sheet against the
stylesheets a page actually loads, so the next unstyled control fails a suite
rather than appearing in a screenshot. It also asserts rendered geometry — both
page fields on one line, equal width, readout below rather than beside, nothing
overflowing the sheet — because "it wrapped" is a layout fact and only a browser
can report it.

The output dimensions moved from the page-range readout to under Size, which is
the control that changes them.

**The help drawer described none of it.** Three user-visible changes shipped
across v142-v144 and "How it works" still told Flip users that Post gives them
"a link" — the sentence the Pad's copy had already outgrown, which is the same
Pad/Flip asymmetry the title feature existed to close. The help now covers the
compose step, stylus pressure (including that a mouse is unaffected, without
which a mouse user reads the feature as broken), the GIF background choice, and
that Size and Pages do not apply to PNG.

`verify_help.py` guards it two ways. Each accordion's hand-typed "N tips" badge
is compared against the number of items rendered inside it — in a BROWSER, on
both surfaces, because the template carries both arms of every `{% raw %}{% if is_flip %}{% endraw %}`
and a source-level count is wrong by construction. The Drawing tools badge had
already drifted by one the moment the pressure tip was added. The second guard
asserts a phrase per shipped feature, so a feature that lands without its
documentation fails a suite.

**Your Skribls — a post used to be unfindable the moment you closed the tab.**
There are no accounts, so a share link is the only handle on a post, and nothing
told anyone to keep it. The id existed on the server; the person who made it had
no way to name it. `static/lib/posted.js` keeps the list and
`static/lib/postedui.js` draws it — shared, because app.js and flip.js already
duplicate two controllers and a third copy is not the answer.

NO PAYLOAD IS STORED — id, url, title, kind, page count, timestamp, and nothing
else. Payloads run to hundreds of kilobytes and localStorage is a ~5MB budget
shared with the crash-recovery autosave, which matters more than this list does.
`verify_posted.py` asserts the whole entry is under 400 bytes and contains no
strokes and no data URL.

It is NOT an account and says so in the footer. Someone who reads it as one will
clear their site data, lose the lot, and be right to blame the app. A local-only
save — Pad's fallback when the server is unreachable — is deliberately NOT
listed, because it has no link and putting it among links you can send would be
a lie. Removing a row removes the row: the suite posts, removes, and then reads
the Skribl back off the API to prove it survived.

`verify_seam.py` caught a `'/s/' + id` fallback in the tray while this was being
written — the exact route literal v132 removed from flip.js, which silently
posts the wrong URL under a url_prefix. It reads `SKRIBL_PLAYER_BASE` now. The
guard has now flagged code written in the same session as itself three times.

**A Jinja comment is not an HTML comment.** The usage example in
`_skribl_posted.html` was written between `<!-- -->`, and Jinja evaluates tags
inside HTML comments — so the partial included ITSELF 973 times before Jinja
gave up. Use `{# #}`.

**The rate-limit copy said the wrong thing.** "You're posting too fast — please
wait a while" scolds, and leaves the question someone actually has ("did I just
lose my animation?") unanswered. Both 429 messages now state the limit and that
the work is safe. The limiter does not track when the window lifts, so the
message cannot yet say WHEN — a `Retry-After` needs the oldest event in the
window and is still open.

**Tooltips were native, patchy, and unstyleable.** 125 buttons across the
templates, 33 with a `title` — and the export, music and image drawers had
none at all. A native tooltip also cannot be styled: not the corners, not the
colour, not the delay. It is operating-system chrome, so rounding one means
not using it.

`static/lib/tooltip.js` moves every `title` to `data-tip`, removes the title
(leaving it shows BOTH tooltips, ours at once and the browser's a second
later), and draws a rounded bubble that flips below when there is no room above
and clamps to the window. Hover AND keyboard focus, because a tooltip only
reachable with a mouse is a mouse decoration. `aria-label` is left alone and
`aria-describedby` is used where there is none, so the text is not
sighted-only. Suppressed entirely on coarse pointers: there is no hover on a
phone, and a tooltip there fires on tap and covers what you just pressed.

**The first tooltip pass covered Flip and missed Pad entirely**, because it
was keyed by element id and the two surfaces name the SAME controls
differently: Flip has `musicBtn`/`imageBtn`, Pad has `musicOpenBtn`/
`musicOpenBtn`. Two more, `addcopy` and `addblank`, are built in `flip.js`
rather than a template, so no template-wide pass could reach them at all.

The durable fix is not the missing tooltips, it is that nothing counted them.
`verify_tips.py` now walks every visible control on both surfaces, opens the
drawers, and fails naming what it found — a list of ids to check would carry
the same blind spot as the pass that created the gap.

**The contract is ICON-ONLY controls.** The first version of that check
demanded a tooltip on everything and flagged buttons that already read "Save
draft" and "Transparent". A tooltip repeating a visible label is noise, and
noise is what makes people stop reading tooltips at all. If a control shows no
words, it must say what it does on hover; if it shows words, it must not.

**First-use hints, because a tooltip cannot teach a gesture.** The magnifier
zooms the CENTRE; aiming it needs scroll or space-drag, which was documented
only in the help drawer under a SEPARATE heading — findable only if you already
knew to look. `static/lib/hints.js` shows one short toast the first time such a
control is used, once ever, persisted in localStorage.

**ONE hints setting, surfaced on both editors.** `lib/hints.js` stores it under
a single key for the whole app, so off on Pad is off on Flip — and the seen-list
is shared too, meaning a hint read on one surface never reappears on the other.
Both menus show the control, because a user on Pad should not have to open Flip
to turn tips off. Two switches over one setting is only confusing if they can
disagree; a `storage` listener keeps two open tabs in step, and each menu
re-reads on open.

Pad's magnifier centres exactly as Flip's does, so it now shows the same hint
under the same key. `verify_tips.py` asserts the cross-surface behaviour
directly: turn it off on Flip, open Pad, the switch reads Off; learn the
magnify hint on Pad, open Flip, it is not taught again.

**Turning tips back on also forgets what has been seen.** Otherwise the switch
silently does nothing for anyone who has already dismissed them, which is a
setting that lies. The toggle also re-reads the stored state every time the
menu opens rather than once at load, because a switch showing the opposite of
what is stored is worse than no switch — `verify_tips.py` caught exactly that.

**The wordmark said "FM" on a phone with 104px of free header space.** The
abbreviation kicked in below 440px, tuned for a header that ALSO held fps,
onion, grid, draw-on and more inline. Those controls moved into the settings
button and the breakpoint was never revisited — a classic leftover: the fix
outlived the problem.

The wordmark is **FLIPMODE**, one word, and it shows from 360px up — every
phone in use, an iPhone SE being 375. FLIP covers 320-359 and FM only below
320, narrower than any phone sold.

**The first attempt got the breakpoint wrong by 80px, and the method is why.**
It summed the header children's widths and called the remainder "free space",
which concluded FLIPMODE needed 440px. But flex shrinks the controls before
anything overflows, so that figure reports room that is not there — and hides
the squeeze when there is. Forcing each candidate into the DOM and reading
`header.scrollWidth` against `clientWidth` gives the real answer: zero overflow
at 360, 9px over at 340, 29px at 320.

`verify_ux.py` checks the tier at seven widths and asserts real overflow at
each, not arithmetic.

**The grid was a div painted with CSS gradients, and it had three faults.**

  1. **Top-left justified.** A gradient repeats from the origin, so a line lands
     on 0% but the CLOSING edge gets none — the grid saturated the top and left
     borders and stopped short of the bottom and right.
  2. **Phantom lines.** Percentage stops land on fractional pixels; a 1px line
     at x=103.6 paints as two dim half-lines, so parts looked doubled and parts
     looked faint.
  3. **The inset was stale.** `syncGrid()` subtracted a hard-coded 1px border
     while the canvas border had become 2px, so the whole grid sat a pixel off
     centre and the corners fought the rounded frame.

None of the three is fixable in CSS. It is a `<canvas>` now: `drawGrid()` places
every line on a whole DEVICE pixel with `fillRect`, draws the closing edges
explicitly, clamps the last line inward so it lands inside the canvas, and reads
the inset from `getComputedStyle(pad).borderTopWidth` instead of assuming it.
Density lives in JS too. The fine 16x12 layer USED to be omitted below 560px,
a gate inherited from the gradient era: percentage background-size put lines on
fractional pixels, so at ~10px spacing the fine layer rendered as an uneven
wash. Snapping to whole device pixels removed that cause and the gate outlived
it — a phone was left with 43px cells and nothing between them. The subdivision
now runs at every size: majors stay 8x6 so the coarse landmarks remain
countable between frames, and the sub-cells add halves at 21.6px on a 346px
phone canvas.

Two assertions in `verify_ux.py` had encoded the old behaviour. One expected
the phone to have major lines only; the other sampled a "cell interior" at
1/16 x 1/12 — which is exactly where a fine line now falls, so it was reading
the grid's own line and calling it a smear. Both were measuring the gate rather
than the property, and the property is EVENNESS: equal gaps, one opacity per
tier. That is what is asserted now, at both sizes.

`verify_ux.py` samples the rendered canvas at three device-pixel ratios: insets
equal on all four sides, alpha present on every closing edge, and ZERO inside a
cell. It also counts vertical lines along a scanline — 17 on desktop, 9 on a
phone — rather than reading CSS, because there is no CSS left to read.

**The last grid column was narrower than the rest.** `paint()` clamped only the
CLOSING line inward — `if (x > W - line) x = W - line` — which kept it on the
canvas but stole its width from the final cell alone: 129, 129, 129, 129, 129,
129, 130, **126**. One narrow column on the right edge is exactly the kind of
defect that reads as "the grid is off" without being obviously wrong anywhere
you can point at, and it survived a check whose tolerance was 4px.

Laying the lines out over `(W - line)` rather than `W` puts the closing line at
the edge by construction and leaves every gap equal. Measured after: spread of
**0** device pixels on both phone and desktop, down from 4. The assertion's
tolerance is now 1.

**The grid is a `<canvas>`, and that matters twice over.** A canvas still
paints its CSS `background-image`, so a leftover gradient rule under it draws a
SECOND grid straight through the first — which is what an earlier attempt at
"fixing the grid" by editing `background-image` would have produced. There is
no such rule now, and `verify_ux.py` asserts `backgroundImage === 'none'` so
one cannot be reintroduced.

The lines themselves are painted at integer DEVICE-pixel positions by
`drawGrid()`. The old percentage-based gradient grid put every line on a
fractional pixel and let the browser round each independently, which is what
made the columns look irregular. Measured from the rendered pixels: 8 columns
at 129-130 device px on a phone, 16 at 85-86 on desktop — a spread of at most
4, which is rounding, not drift.

The suite SEARCHES for a sample row that crosses verticals rather than assuming
one. Sampling blind at H/12 landed exactly on a horizontal line at desktop and
reported "1 line" — a measurement that looked like a catastrophic failure and
was actually a bad probe.

**The colour drawer was sliced by the browser's own toolbar on a phone.** Two
causes, both needed:

* `.flip-drawers` had ZERO bottom padding, and the drawers are the last thing
  on the page — so on iOS Safari, whose bottom toolbar OVERLAYS the viewport,
  the swatch row and the eyedropper sat underneath it. Measured at 393x852 the
  drawer already ended 12px past the fold before the toolbar took its ~60-90px.
* `refitDrawer()` scrolled with `block: 'nearest'`, which moves the MINIMUM
  amount — a drawer already partly on screen got no scroll at all, so it stayed
  permanently half-visible. `block: 'end'` brings its bottom to the viewport
  bottom, where the new safe-area padding keeps it clear of the chrome.

Both editors got the padding; `.tab-panel` had the same exposure on Pad.

**The Saving pill sat on top of "Clear all pages"** whenever a drawer was open.
It is fixed to the bottom-left and the drawer scrolls under it. A transient
advisory covering a destructive control is worse than one you cannot see, so it
fades out while any drawer is open.

**Two colour swatches showed as selected at once, and the cause is a JS
footgun worth knowing.** `setColor()` did:

    d.classList.toggle('active', d.dataset.color && d.dataset.color... === hex)

The custom swatch has NO `data-color`, so that expression is
`undefined && ...` -> **undefined** — and `classList.toggle(name, undefined)`
is treated as *no second argument*, which TOGGLES rather than forcing off. Every
colour change therefore flipped the custom swatch's ring on and off, leaving two
swatches highlighted and the wrong one appearing current.

Pad was unaffected because it passes `b === btn`, always a real boolean. The fix
is `!!`, and a sweep of every `classList.toggle(name, X)` in the tree found this
was the only expression that could yield undefined — the rest pass genuine
boolean flags.

`verify_ux.py` clicks through five presets on BOTH surfaces and asserts exactly
one swatch is selected after each. A single check at load could pass by luck,
because the state flipped on every call.

**The wordmark was 15px on a phone and 17px on desktop**, so the brand read
visibly lighter on the device most people use. Same block as the "FM"
abbreviation, same cause: a header that also held fps, onion, grid and draw-on
inline. The controls moved into the settings button; the shrink stayed. At 17px
the header overflows by ZERO at 375, 393 and 430.

**The grid's finest level was noise on a phone.** Three nested gradient layers
at 12.5% / 6.25% / 3.125% of the canvas width. The finest is 21px on a 673px
desktop canvas but **10.8px on a 347px phone canvas** — below the point where a
grid reads as a grid, and at that spacing the 1px lines land on fractional
pixels and render unevenly. Below 560px the finest layer is dropped and the
remaining two are lifted slightly, leaving 21.7px spacing.

Both are the same shape of mistake as the abbreviation: a compromise made for a
denser layout that outlived the layout. `verify_ux.py` checks wordmark size
parity against desktop at four widths, and the grid's layer count and spacing
at two.

**The onion icon was drawn at stroke-width 1.1** while every neighbour in the
header is 1.9-2, with four curved paths converging inside a 34px circle. At
actual size on a dim panel it mushed into a blob — thickening it did not help,
because the interior lines merge. Replaced with a three-sheet stack. THREE, not
two: the depth control beside it is 1/2/3, so a two-sheet icon would quietly
contradict its own setting. The NAME stays "Onion skin" — it is the correct
animation term and only the drawing was wrong.

`verify_ux.py` now compares stroke weights across the whole header and fails if
one icon is drawn meaningfully thinner than the rest. Its first version counted
FILLED glyphs too — the play triangle and the `...` dots report stroke-width 1
because nothing sets it and it is never drawn — and failed on two icons that
are perfectly legible. It looks only at `fill: none` icons now.

**Move artwork — dragging a page's drawing to new coordinates.** The first
transform in the app, and deliberately the SIMPLEST one: the whole page moves,
nothing is selected. Copy a page, nudge the drawing, repeat — the pegbar
workflow that frame-by-frame animation has used for a century.

**It lived in the PAGE BAR, and as of v226 it does not.** The original argument,
kept because the second half of it is still load-bearing: *moving a page's
artwork is a page operation, and it belongs with Copy, Hold and Delete; the tool
row is also full on a phone. Entering the mode REPLACES the page bar with a
transform bar rather than adding one, because a second bar would push the
filmstrip off screen exactly when it is needed to judge the move.*

The first clause was wrong and the second stopped being true. It is not a page
operation — it moves the DRAWING, which is the one thing in that row that was
not a page. And the tool row is no longer full: the tool shelf overflows into a
tray, so a sixth tool costs no width at any size. Artwork is a tool now, beside
Select and Liquify. The transform-bar behaviour above is unchanged.

It kept the name "Artwork" rather than becoming "Move" — originally because the
page bar's two reorder buttons were both labelled "Move", which v226 also fixed
by labelling them Left and Right. The name stays anyway: in a shelf of verbs
(Pen, Eraser, Shape, Select, Liquify) the noun is what distinguishes moving the
art from moving the page.

**Undo stores the INVERSE OFFSET, not a snapshot.** A translation is exactly
reversible, so undoing is applying -dx,-dy to the same points. With `& after`
on a 62-page animation a snapshot would copy every affected page; two numbers
cost nothing. It cannot be bit-exact — adding then subtracting a float does not
reproduce the original — but the round trip lands within 2e-14 canvas units,
and `verify_move.py` asserts to 1e-6 rather than asserting a property of IEEE
754.

**An action log records the ORDER of undoable actions.** Flip's undo pops
stroke groups; without the log, undo after "draw, move" would pop the stroke
and silently leave the move in place — undoing something the user did not do
last. The suite drives exactly that sequence.

**The offset is applied to a working COPY of the original points.**
Accumulating onto the live coordinates would round-trip them on every pointer
event and drift the drawing over a long drag. Reset then becomes "offset zero"
and lands exactly.

**The drag is measured in canvas units, not screen pixels** — `CW / rect.width`
— so it tracks the pointer at any zoom or display scale. Raw `clientX` would
move the drawing faster or slower than the finger whenever the canvas is not
1:1, which it never is on a phone.

**The cursor is set INLINE.** `setTool()` writes `pad.style.cursor='none'` for
the custom brush cursor, and an inline style beats any stylesheet rule however
specific — the first attempt styled `.flip-stage.moving #pad` and the grab
cursor never appeared.

**Thumbnails repaint on pointer release, not per move event.** Repainting 62 of
them on every frame of a drag is what would make the feature feel heavy.

WHAT THIS SETS UP. Selection — moving PART of a drawing — reuses all of it: the
mode, the bar, the offset readout, Reset, Done, Escape-to-cancel and the undo
mechanism. Only hit-testing and a selection overlay would be new, and the
readout changes from an offset to a count. That was the argument for building
the whole-page move first.

**Dismissing a re-add card turned its dot GREEN.** `refreshPendingCards()`
sets the tab dot `hidden = false` in its pending branch, and the else branch
dropped only the `pending` CLASS — never restoring `hidden`. So dismissing left
a visible dot with no pending styling, which renders in the "has media" green,
until `syncMusicUI()` next ran and hid it. That is why the green vanished when
you opened the drawer: opening was not clearing a stale state, it was the only
thing ever fixing it. Both branches now restore `hidden` from whether media
actually exists, and the suite asserts that opening the drawer is a NO-OP
rather than the repair.

**The Move arrows now explain themselves, once.** Below 560px the pagebar
labels are hidden, so Move is two bare arrows in a row that also reads
"Page 62 / 64" — they look like navigation while they REORDER the animation.
A page glyph was tried in v151 and reverted: at 11px a rounded rect renders as
a zero. A hint says it at the moment it happens and names the new position, so
the effect is legible even if you were not watching the strip.

**Hints moved to the TOP of the screen.** At `bottom: 96px` the page-move hint
landed squarely on the filmstrip — covering the thumbnails it tells you to tap.
Flip's bottom chrome is ~230px tall and Pad's is ~90, so no single bottom
offset clears both.

**Three controls were sized by accident rather than intent.** `#fps` was a
bare `.seg` on the default height while `.onion-seg` overrode it to 26, so
Speed rendered visibly larger than Onion skin directly beneath it. The onion
tint toggle was 28x26 — wider than tall, and 4px proud of the segments — which
read as a box rather than a round toggle once its active state gave it a
background. And in the header, `.tool-open` is 44x44 with `.onion-tool`
overriding to 34; `.tune-tool` did not, so the settings button stood 8px taller
than the onion toggle, the post button and the `...` beside it.

The pattern is one class overriding a shared base and its sibling not
following. `verify_ux.py` measures the SPREAD across a row rather than pinning
individual pixel values, which is the check that finds the next one of these
instead of this one again. Found by walking every visible control on both
surfaces, grouping by row, and flagging any row with a height spread of 6px or
more — Pad had none, Flip had two.

**The canvas floated in empty space, and capping the scale at 1:1 made it
worse.** At the 300,000px preset target, 4:3 was 632x474 — a 43px gutter each
side of the 720px app column, and in Pad **127px of dead space above AND
below**, because Pad's canvas area is far taller than Flip's: Flip's is 560px
with a filmstrip and page bar under it, Pad's is 728px with nothing.

The proper fix — grow the canvas and redraw at the larger resolution — is not
available: Pad holds its drawing in a raster dry/wet buffer keyed off
`canvas.width`, with no redraw-from-strokes path, so resizing the backing store
live would erase the drawing. Recorded here as the reason, because it looks
like the obvious fix and is not.

**Downscaling is sharp; only upscaling is not.** So the target rose to 500,000
— 4:3 is 816x612, 16:9 944x531, 1:1 707x707, 9:16 531x944, all still exact
ratios within 0.4% of each other on area. The canvas now renders at 694x521 on
a desktop: it fills the column, is DOWNSCALED to get there, and stays crisp.
Side gutter 43px -> 12px, vertical 127px -> 104px. The rest is inherent — a
fixed-aspect rectangle centred in a taller area leaves margin, and that is what
centring means.

The ceiling on this is export weight, not memory: 'Full' export is native size,
so a bigger canvas is a bigger GIF, and the Size control exists for anyone who
wants smaller.

**The two editors showed the same canvas at different sizes, and the bigger
one was the worse one.** Both author 632x474, but Flip DISPLAYED it at 694x521
and Pad at 632x474. `canvas.width` is `authored x dpr` on both surfaces, so
Flip's `fitPad()` cap of **1.4** stretched a fixed bitmap: every line in Flip
was ~10% softer than the same drawing in Pad, which had always clamped at 1 in
`layoutEditorCanvas()`. Flip is capped at 1 now — the smaller canvas is the
sharp one.

**Pad reserved no breathing room while Flip reserved 24px**, so on a narrow
screen Pad's canvas pressed against the column edge, and after the ring was
added the ring sat flush against the app border. `.canvas-area` now has the
matching padding — and `layoutEditorCanvas()` subtracts it, because
`getBoundingClientRect()` reports the BORDER box and was handing the reserved
space straight back.

`verify_canvas.py` compares both editors at four viewports and fails if they
differ by a pixel, and separately asserts neither is displayed larger than its
own bitmap.

**A tally on its own line drifted above a later section for the SECOND time**,
reporting a green undercount with nothing listed as failed. `ok` is now
computed at the point of use, so there is no line left to drift.

**The canvas edge vanished the moment you started drawing.** `.canvas-wrap.recording`
replaced `box-shadow` wholesale, dropping the ring added the release before —
and Pad enters that class on the FIRST STROKE, so the edge disappeared exactly
when it was needed. `.light-bg` did the same. The ring is now a
`--canvas-ring` variable that every state carries forward, and `light-bg` gets
a DARK ring, because a white ring on a white canvas is not an edge. Checked
mid-stroke, not at rest: a rest-state assertion cannot see this.

**Pad's canvas was square and Flip's was rounded.** Two editors in one app
should not disagree about the shape of the thing you draw on. Pad now uses the
same `--r-frame`.

**A stroke ended when the pointer crossed the canvas border.** `app.js` bound
`mouseleave -> endDraw`, so sweeping a line out past the edge and back produced
two strokes with a gap. Touch never had it — there is no `mouseleave` — which
is why the same gesture behaved differently on a phone, and why Flip was fine:
Flip binds `pointerup` on WINDOW and uses `pointerleave` only to hide the
cursor. Pad now tracks movement on `window` while drawing and ends on release
anywhere. A stroke that ends where you did not lift the button is a stroke you
did not draw.

**Tips and Canvas are the same width.** Two right-aligned switches of different
widths left a 99px hole between the word "Tips" and its control while "Canvas"
sat snug against its own.

**The drawing surface had no findable edge.** `#pad`'s border was
`--hairline-strong` — `rgba(255,255,255,.09)`, about 4% from the page behind
it. That reads fine on a good panel and disappears entirely on a dim or
low-contrast monitor, leaving no way to see where you can draw. Both canvases
now carry a 2px edge plus a faint outer ring; the ring is the part that
survives a display crushing blacks. Pad's `.canvas-wrap` had only an inset
vignette and got the same treatment.

**Your Skribls marked a Flip with a hatched square.** `U+25A6` matched nothing
in the app — a Flip is identified by the open book that opens it from Pad's
header — so the tray disagreed with the header about what the thing is. The
Pad entry's `U+270E` pencil also leaned the opposite way to the Pen tool, so a
replay carried a pencil facing away from the one the user drew with. Both are
inline SVG now, because the two characters rendered at whatever weight and
baseline the system font chose and sat unevenly beside each other.
`verify_posted.py` compares the tray's book path against the header's by
geometry — a different book would pass a "has an svg" check.

**A hard server failure looked like a dead button.** Every `POST /api/skribls`
was returning 500 — `psycopg.OperationalError: failed to resolve host
'dpg-...'`, i.e. the Render Postgres instance had become unreachable. The
client reported that only as a transient chip, which on a phone is easy to miss
entirely, so it read as "the share button does nothing". THREE client-side
theories were chased before a server log settled it in one line.

The lesson is about diagnosis, not code: the failure was reported from a phone,
so the search started in the client, and the request had a Windows Chrome user
agent all along. **Check the server log before theorising about the client.**

A failed post now writes into the share sheet itself and stays there until the
next attempt, distinguishes 5xx ("the server could not save it") from 4xx ("the
server refused it"), says in both cases that the drawing is safe, and leaves
the sheet usable so retrying is one tap. `verify_flipmeta.py` drives 500, 503
and 400 through intercepted routes and asserts a visible message, an intact
sheet, an unstuck `sharing` flag, and that a stale failure is cleared before a
retry rather than sitting above it.

**26 unguarded bindings could abort the file, and did so silently.** `flip.js`
had 26 `document.getElementById(id).addEventListener(...)` chains with no null
check, and `app.js` had 17. A null from ANY one throws a TypeError at the top
level, which aborts the remainder of the script — so every binding written
after the failure never happens. `postBtn` was bound at line 1949, after most
of them. That is precisely the shape of "share does nothing while everything
else works", reported from an iPhone and not reproducible here.

All 43 now go through `bindEl()`, which logs and skips a missing element
instead of throwing. The share binding also moved to the earliest point its
handler exists, because share doing nothing is the worst failure in the app —
it is the whole point of it. `openShareCompose()` no longer has a silent early
return: a busy state says "Still posting…", and a missing sheet says so and
names itself in the console.

This is a fix for the CLASS of failure, not for a diagnosed line. The iPhone
bug is still unreproduced — WebKit cannot be installed in this container — so
`lib/report.js` also captures `console.error`/`console.warn` alongside `error`
and `unhandledrejection`, and loads FIRST so it sees failures in the editors.
A control that quietly stops working on a device we cannot reach now names
itself in a report the user can copy.

**Segmented controls showed no selection until you tapped one.** `.seg-slider`
is `opacity: 0` until something positions it, and positioning needs the button
laid out — `offsetWidth > 0`. Inside a sheet or menu that ships `hidden` that is
never true at init, so the one-shot call bailed and the pill stayed invisible.
Reported from a phone, where layout lands later than on desktop: Flip's export
sheet opened with no pill on Size or Loops, and Pad's canvas row showed no
selection at all.

`app.js` had already solved this for the DYNAMICALLY built zoom/magnify groups
with MutationObserver + ResizeObserver; the groups written directly into
templates never got the same treatment. `static/lib/segslider.js` is that
treatment, shared. The ResizeObserver is the one that matters — it fires when
the group finally gains layout, i.e. when the sheet containing it is shown.

**The report sheet now captures JS errors.** A bug reported from a phone
("share does nothing") is unreproducible without the exception behind it, and
iOS Safari has no console without a Mac and a cable. A silent failure is almost
always an exception thrown before a handler was bound, so the exception is the
single most useful thing a report can carry. `lib/report.js` installs
`error` and `unhandledrejection` listeners and now LOADS FIRST, before the
editor scripts, so it catches failures in them. Bounded at five entries.

**Flip's menu had no keyboard exit, and its new scrim had no click handler.**
It closed on an outside click and nothing else. Every other dismissible surface
in the tree already handled Escape — the export sheet, the tune panel, the help
drawer, and Pad's own menu at `app.js:1656` — so this one menu trapped you. It
mattered less before the menu gained a full-screen dim; a scrim with no
keyboard exit is a dead end, and dimming the page implies tapping the dim
dismisses it. Both added, and `verify_ux.py` checks the state that actually
breaks a session: that a scrim is never left painted over the page after the
menu is gone, swallowing every subsequent click.

Found by a sweep that drives both editors and the player through every menu,
export, share, undo/redo storm, page operation and canvas switch at two
viewports while watching for page errors, console errors, failed requests and
4xx/5xx. That sweep now reports zero problems.

**`.seg` was defined in flip.css while `.seg-slider` was in styles.css, and
Pad does not load flip.css.** So the moment Pad gained a `.seg` canvas picker,
its container had no `position: relative` and the absolutely-positioned slider
stretched against the menu sheet — painting a solid purple bar down the entire
menu and hiding half the items. Both halves live in `styles.css` now.

**Every functional assertion passed on that build.** The buttons existed,
applied their sizes, marked themselves selected, and locked after drawing;
`verify_padcanvas.py` was 21/21 green. Only a screenshot showed it. The suite
now measures the slider's box against the segment's box and fails if it
escapes, which is the class of check that was missing: what a control DOES was
tested, what it LOOKS like was not.

**The Move buttons' page glyph was tried and REVERTED.** At 11px a plain
rounded rect renders as a zero, so on a phone the buttons read "◀ 0" and
"0 ▶" — a number, not a page, and worse than the bare arrow it replaced. The
repeat glyph on Hold works and stays. `verify_hold.py` pins the absence so the
rect is not helpfully reintroduced; anything legible enough to mean "page" at
that size needs more detail than 11px can carry, so widen the button and use a
word instead.

**verify_postgres.py has run, for the first time in the project's history.**
14/14 on PostgreSQL 16.14 with four gunicorn workers: twelve simultaneous posts
against a quota of two admitted exactly two, refused ten, committed exactly two
rows, stranded no reservations, and killed no workers. This is the bug the v141
rate-limiter work exists to fix, and SQLite cannot exercise it — it serialises
writes and hides the fault completely. Reproduce with:

    SKRIBL_PG_DSN=postgresql://user@host:port/db ./harness/run_harness.sh verify_postgres.py

**The page bar was unreadable on a phone.** Below 560px every `.pb-tx` label
is hidden, which is the right call for space — but it left `×1` bare, and
left Move as two unlabelled arrows in a bar that also reads "Page 10 / 12". The
arrows therefore looked like page NAVIGATION while actually reordering the
animation, which is the worse of the two because acting on the misreading
changes the work.

Each now carries a glyph that does the job the label did: a repeat symbol on
Hold, a page symbol on the Move pair. The Move glyphs disappear again at 560px
where the words return, because a glyph beside its own label is decoration.

The glyphs sit OUTSIDE `.pb-ic` deliberately: `flip.js:752` rewrites that
element's `textContent` on every render, so an svg inside it would survive the
first paint and vanish on the first page change. `verify_hold.py` clicks
through a hold, a move and a rebuild and re-checks — a single-state assertion
would have passed on the broken version.

The section runs at a 390px viewport and asserts FIRST that the labels really
are hidden there, because at 1280px the labels are present and every assertion
after it would pass for the wrong reason.

**There was no way to report a problem, and no way to find a Skribl again.**
Both are release blockers for a test with real people, and neither needs a
schema change.

`static/lib/posted.js` keeps a list of what this browser has posted — id, url,
title, kind, page count, timestamp. No payload, so it stays a few kilobytes
however many are made. The UI says "saved in this browser only" because a
tester who reads it as an account will lose work and blame the app. Removing a
row removes the row, not the Skribl; `verify_posted.py` asserts the post is
still on the server afterwards, and that a corrupt or non-array localStorage
reads as an empty list rather than crashing the editor.

`static/lib/report.js` collects version, browser, canvas, page and point counts
onto the clipboard. It COPIES; it does not send. There is no endpoint, and
adding one would mean an unauthenticated write path, storage, and someone
reading it — so the button says "Copy details". `verify_report.py` asserts the
copy never claims to send, because a tester who believed it would wait for a
reply that was never coming.

**The report must not carry unpublished work**, so titles, captions, stroke
coordinates and media are excluded. The suite seeds a title that appears
nowhere else and requires it absent, which catches any field added later that
happens to carry content.

**Reading editor state off `window` was silently wrong.** Top-level `let` never
becomes a window property, so `window.CW` is undefined — while `window.frames`
is the browser's built-in frame collection and `window.fps` is the element with
`id="fps"`, because ids become window properties. The first collector reported
`fps: [object HTMLSpanElement]` and no page count at all. Classic scripts share
one global lexical scope, so a BARE identifier resolves to the editor's
variable; `lex()` evaluates one through a Function so an undeclared name throws
into the guard instead of aborting the collector. Any future code reaching
across these files has the same trap waiting.

**Pad's canvas shape depended on the browser window.** `resizeCanvas()` called
`establishEditorCanvas(area.width, area.height)` once from whatever the
available area happened to be on first load, and Pad had no size control at
all. Two people drawing the same thing got different aspect ratios; the same
person got different ones on phone and desktop; none of it was chosen. For a
feed, where every card would be a different shape, that is unworkable.

The preset table moved to `static/lib/canvassizes.js` — copying Flip's list
into `app.js` would have made a second copy of a list that has already drifted
from its own labels once. Pad now gets the same four presets, in the same
markup, with the button labels written from the table at runtime so a rename
there cannot leave a stale label in the markup.

**Pad locks the canvas once you have drawn, and Flip does not.** This is the
one place the two surfaces must differ. Flip's pages are independent and
resizing simply keeps coordinates. Pad records stroke TIMING, so resizing
mid-take would change the space a replay is drawn into partway through the
recording it replays. The canvas is free while empty and refuses afterwards —
refuses with an explanation rather than silently ignoring the click, and never
by destroying the take. `verify_padcanvas.py` asserts the refusal, that the
drawing survives it, and that the button does NOT light up for a size that was
never applied.

The first assertion in that suite is the one that would have caught the
original bug: load Pad at 1280px and at 520px and require an identical authored
canvas. A single-viewport suite structurally cannot see it.

A canvas matching no preset reports as `custom` rather than the nearest match —
every Skribl authored before Pad had a picker is a custom size, and quietly
relabelling one would misreport what it actually is.

**Two of Flip's four canvas presets did not match their own labels.** `4:3`
was 640x460 (1.391 — off by 4.3%) and `9:16` was 420x640 (0.656 — off by 16.7%,
nearer 2:3), so someone picking 9:16 for a phone-shaped animation got something
noticeably wider. A label and a pixel pair were typed side by side and nothing
compared them.

Sizes are now integer MULTIPLES of their ratio — exact by construction, not by
rounding — scaled to a common target area so payload size and export time stay
comparable across presets. A constant long edge would not have done that; it
would make 1:1 78% more pixels than 16:9 for no reason a user could see. The
set is 632x474, 736x414, 548x548, 414x736. `16:9` shifts from 720x405 to
736x414; both are exact, the new pair matches its siblings. Existing drawings
are unaffected — every payload carries its own `canvasSize`.

`CW`/`CH` initialised to a SECOND hardcoded 640x460 that had to agree with the
table by hand, and once the table was corrected it agreed with nothing:
`currentSizeId()` reported `custom` on a fresh canvas. Both now derive from
`FLIP_SIZES[0]`. `verify_canvas.py` cross-multiplies each label against its
dimensions as integers — a float compare passes on a pair that is merely close,
which is the whole failure — and its expected sizes are read from the table
rather than repeated in the suite.

**Flip's overflow menu had no backdrop.** Pad dims and blurs behind its menu
via `.menu-overlay::before`; Flip's `.flip-menu` was a bare positioned div with
no scrim at all. Added as a real element rather than a pseudo-element: clicks
on a `::before` register on its parent, so a scrim built that way would have
swallowed the outside-click that closes the menu. Same alpha and blur as Pad.

**The filmstrip did not follow a restored page.** `buildStrip()` rebuilds the
strip's children, which resets `scrollLeft` to 0. `applyPayload()` restores
`idx` but nothing scrolled, so a 62-page animation reopened on page 62 with the
strip parked at page 1 and the active tile highlighted off-screen. `addFrame()`
was the only caller that scrolled — the fix existed and was never shared. Now a
`scrollStripToActive()` helper, called from `addFrame`, `delFrame` and boot;
un-animated on boot, because scrolling from page 1 to page 62 is a second of
strip flying past for no reason. `verify_pages.py` asserts the active tile's
box against the strip's box, since `scrollLeft` alone cannot say whether a tile
is visible.

**Video export repeated the animation twice, and nothing said so.** Both
encoders hardcoded 2 loops, so a 5.2s Flip exported as a 10.3s MP4 while the
header badge still read 5.2s. The doubling is right for a 1.5s clip — video
players do not loop the way GIFs do — and wrong for a 30s one, and only the
person exporting knows which they made. It is now a `Loops: 1 / 2 / 3` control
defaulting to 2, with a readout stating the resulting length.

VIDEO ONLY. A GIF sets `repeat=0` — one pass, looping forever — so repeating
its frames would inflate the file for nothing. The readout says so rather than
letting the sheet imply otherwise.

`exLoopSeconds()` is shared by the readout and both encoders, so they cannot
disagree about a file's length, and `verify_exportui.py` asserts the stated
duration against it at each setting.

**The sheets could not scroll.** Neither `.menu-sheet` nor `.export-sheet`
carried a `max-height` or an `overflow`, so a sheet taller than the window ran
off the bottom with no way to reach it. Found when a fourth options block
pushed the Loops control out of a 900px viewport; it applied to any short
window long before that. Both variants are now bounded and scroll.

**The page fields updated on `change` only**, so a readout lagged until the
field was blurred — you typed a page number and the stated length still
described the previous range. `input` now refreshes the READOUTS while
`change` keeps the clamping, because clamping per keystroke would rewrite "1"
to the maximum while someone was typing "12".

**The help drawer got search, and its counts stopped being typed.** Flip's help
is 46 entries across 7 sections; finding one meant opening up to seven
accordions and scanning. `static/lib/helpsearch.js` filters live, hides sections
with no hits, highlights matches, and offers `/` or Cmd/Ctrl-K to focus. Esc
clears a query before it closes the drawer, so a search is never one keypress
from losing the panel.

It lives in `lib/` **on purpose**. The accordion open/close handler is written
twice — `app.js` and `flip.js` — driving the same partial, and adding search to
both would have made a third copy of the project's largest known-open. Both
surfaces now call `SkriblHelpSearch.init()` against one implementation. If the
lib fails to load, the accordions behave exactly as before.

Every `accordion-count` badge is now DERIVED from the DOM. They were hand-typed,
and one was wrong the moment the pressure tip was added. During a search they
show matches rather than totals — more information from the same pixels, and no
number in the tree that nothing checks.

`verify_help.py` (49) asserts a query reaches more than one section, that
highlights do not nest under repeated keystrokes (the failure mode of rewriting
innerHTML without caching the original), that clearing restores every entry and
removes every mark, and that the empty state appears and retreats. On both
surfaces, because "shared" is a claim until something checks both.

**`[hidden]` was defeated by `display: flex`, for the SECOND time in this
tree, and the test passed anyway.** `.accordion-header` is `display: flex`,
which overrides the UA's `[hidden]{display:none}`, so a no-match search left all
seven sections on screen each showing a "0" badge. The lesson had already been
learned once on the Flip compose pane and written into the primer, and it was
reintroduced regardless.

The more useful finding is why the suite missed it. The assertion counted
elements whose `hidden` PROPERTY was false — which is a check that the JS did
what it was told, not that anything disappeared. It passed while the bug was
plainly visible in a screenshot. It now counts elements with a non-null
`offsetParent`, which is null only when something genuinely is not laid out.
**A property assertion is not a rendering assertion.**

**The search placeholder suggested a term that does not exist on Pad.**
"onion" is Flip-only, so the Pad placeholder led straight into the empty state
— which is what made a working search look broken. The suggestions are now
gated on `is_flip`, and the suite reads the placeholder, searches every term it
names, and asserts each one finds something. A suggestion that points at
nothing is now a failure on whichever surface it points at.

**The search field carries an accent wash, not another neutral surface.** On
`--surface-raised` it sat about 4% from the drawer behind it and read as a
hairline rather than a control. `#161528` is that surface composited with a 6%
accent — written as a flat value rather than an opacity layer so it does not
shift if the drawer's ground moves. The tint also marks the field as the one
INTERACTIVE element among static section cards, and it lets focus deepen a
colour already present instead of introducing one. `verify_help.py` compares
the computed luminance of the field against the drawer and fails if they
converge, because the markup is identical either way and only a rendered
comparison can see it.

**The focus ring doubled, and the cause is worth recording.** A global
`input:focus-visible` rule near the end of `styles.css` draws a 2px outline at
3px offset on EVERY input. Inside a wrapper that already signals focus with
`:focus-within`, that is a second purple ring 3px outside the first — two
concentric rounded rects, most visible along the right edge. A plain
`outline: none` on the input did not help: it sat earlier in the file and lost
to the later rule at equal specificity. Suppressed with a matching selector
instead, and the wrapper's ring softened to a border plus a low-alpha glow.
`verify_help.py` asserts the computed outline is none AND that the wrapper still
shows focus, because removing the ring entirely would trade a cosmetic flaw for
an accessibility one.

Any future control wrapping an `<input>` in this tree inherits the same trap.

NOT built, and worth knowing: the two-tier split of "Getting started" from
"Reference", and reordering the sections so Zoom and pan stops sitting between
the two heaviest ones. Both are template surgery on a partial two surfaces
share, and neither is load-bearing for findability now that search exists.

**Every menu sheet was anchored to the browser window, not to the app.**
`.menu-sheet` was `position: absolute; right: 18px` inside a
`position: fixed; inset: 0` overlay, which pins to the VIEWPORT's edge. The app
is a 720px column centred with `margin: 0 auto`, so on any wider window the
sheet detached and floated in the empty gutter beside the UI — roughly 550px
adrift at 1835px. It looked correct at about 720-760px and nowhere else, which
is the width a phone-first layout gets checked at. `right` is now
`max(18px, calc(50% - 360px + 18px))`, so the sheet tracks the column's right
edge and falls back to a viewport inset when the window is narrower than the
column. `verify_exportui.py` asserts the sheet stays inside the column at 760,
1280 and 1900px — three widths, because testing one is exactly what missed it.

**Pressure is stored as `size`, not as a new field.** A `pressure` key would
have round-tripped — points are not shape-validated and POST preserves unknown
fields — but the player renders from `size` alone, so the editor and the shared
link would have disagreed about what a drawing looks like. Scaling `size` at
capture time means the player, all three exporters, the thumbnail renderer and
every already-released client honour it unchanged, and an old payload is still
a valid new one. This is the same failure the v137 backfill made in the other
direction: trusting a plausible field that nothing downstream reads.

**The two editors gate pressure DIFFERENTLY, and must.** Flip binds Pointer
Events and reads `e.pressure` where `pointerType === 'pen'`. Pad binds
`mousedown`/`touchstart`, where PointerEvent fields do not exist at all — the
first draft of this feature checked `pointerType` in `app.js` and was dead code
that could never fire, which passed source review and was caught only by running
it. Pad reads `Touch.force`, gated on `touchType === 'stylus'` so a finger on a
force-capable screen is not treated as a stylus. Consequence: an Android stylus
draws at constant width, because Android touch events expose no `touchType`.

**Pad's stylus path is UNVERIFIED on a device.** `touchType` is an iOS extension
with no `Touch` constructor support, so an Apple Pencil stroke cannot be
synthesised in Chromium. `verify_pressure.py` asserts the mapping directly
against the function and asserts that real mouse input is unchanged, then SKIPS
the plumbing from `touchstart` into `pressureSize` with that reason printed.
Needs a real iPad. The skip contributes zero assertions and is not coverage.

## Running it

    pip install -r constraints.txt --require-hashes   # the pinned lock
    python -m alembic upgrade head                    # NOT create_all(); it cannot ALTER
    gunicorn app:app                                  # or: flask --app app run

`pip install -r requirements.txt` also works and resolves fresh within the
version ranges. What does NOT work is `-r requirements.txt -c constraints.txt`:
the lock carries hashes, that puts pip in --require-hashes mode, and that mode
rejects ranges. The hashes are linux x86_64 / cp312 — regenerate the lock on your
real deployment target.

## Mounting it in a host application

    skribl.init_skribl(
        app,
        session=lambda: db.session,       # the host's session — one transaction
        url_prefix="/skribl",
        static_url_path="/static",
        current_user_id=lambda: current_user.id,
        csrf=your_csrf_triple,            # (prepare, issue, validate) — see below
    )

`csrf` is a THREE-element tuple `(prepare, issue, validate)`, not a pair:

    prepare()          before_request — resolve the token onto `g` so the
                       template can render it (after_request is too late)
    issue(response)    after_request  — set the cookie, return the response
    validate(request)  -> bool        — checked before any mutating handler

`skribl.security.double_submit_csrf()` returns exactly that triple and needs no
dependencies. Enable it with `SKRIBL_CSRF_PROTECT=1` standalone.

That is the whole contract. `harness/verify_prefix.py` proves it works mounted.

## The harness

`./harness/run_harness.sh $(cd harness && ls verify_*.py)` runs every suite;
all; it writes `harness/LAST-RUN.txt` itself now, and `harness/stamp_docs.py`
stamps the totals into the docs so they cannot drift by hand again.

Green on SQLite and PostgreSQL. `verify_mp4.py` SKIPS without a browser that has
an H.264 encoder — a skip contributes zero assertions and is not coverage.

## Known-open — media associations and opaque store URLs

`skribl_post_media` is reconstructed from payloads by the migration chain, and
reconstruction reads the storage key out of the stored URL. That works for the
LOCAL backend, whose URLs are built by `url_for("skribl.media", key=...)` and
therefore always contain the key, and for S3-style URLs that carry the key in the
object path.

It does NOT work for a custom store returning an OPAQUE url such as
`https://cdn.example/download?id=token`, where the key appears nowhere in the
URL. The v139 repair deleted such associations and no later revision can restore
them, because the mapping is gone.

The practical impact is smaller than it sounds, and worth being precise about:
`/media/<key>` refuses unless the store is a `LocalDiskStore`, so associations
gate NOTHING for a custom or S3 backend — those URLs are served by the bucket or
CDN and never routed through Skribl. A lost row for an opaque store is a
data-integrity blemish, not a media outage. For the one backend where
associations DO gate access, the key is always present in the URL and
reconstruction is complete.

If you run a custom store and want the rows back, restore them from a pre-v139
backup; nothing in the chain can derive them.

## Known-open

### Closed in this session

**`[hidden]` no longer needs a per-element rule.** `styles.css` now carries
`[hidden] { display: none !important; }`. The UA's `[hidden]` rule loses to any
author rule, including a same-specificity one like `.pagebar{display:flex}`, so
`el.hidden = true` silently drew nothing for most of the app: a sweep of both
editors found 380 such elements on Flip and 366 on Pad. The move bar's own
`.movebar[hidden]` was the fourth one-off fix for this; the rule generalises
them. Checked safe first — no element on either surface carried `[hidden]` while
still rendering, so nothing depended on the defeated behaviour — and confirmed
after by a full-page pixel diff of both editors at load, which is identical
apart from one 6x6 region that differs between two runs of the SAME build.

**The move bar's page bar actually hides.** `#pagebar` rendered 55px tall with
`hidden === true` through every version of Move artwork, because
`verify_move.py` asserted the PROPERTY. It now asserts `offsetParent`, computed
`display` and rendered height, and fails on unmodified v179.

**Segmented controls state their height.** `--seg-h` was declared in four places
and read in none, so a `.seg` took its height from `font: inherit` ->
`line-height: inherit` — it was as tall as whatever contained it, and it
followed the VIEWER'S installed font. The same stylesheet rendered `#hintSeg` at
20px in headless Chromium and 23px on the owner's Mac while `.pb`, which states
`height: 38px`, matched exactly. `.seg` now reads `var(--seg-h)` with NO
fallback: an undefined `var()` computes `height` to `auto`, so a control that
has not been measured keeps its current behaviour and opting one in stays a
one-line decision. Only `.mb-scope` and `.mb-offset` opt in so far, both at 30px
— the app's existing secondary-control size (`.eyedropper-btn`, `.color-dot`,
`.bg-swatch`, `.zoom-val`, `#musicPendingBtn`). The four dead `--seg-h: 26px`
declarations were REMOVED rather than left looking like decisions: 26 rendered
nowhere, and pinning the others would mean choosing a number for every viewer
from a measurement taken on one machine.

### Move artwork is transactional (external abuse pass)

A session-wide origin snapshot, a frozen page set, and a redo.

* **Scope could not be changed after moving.** `captureMoveOrigin()` captured
  only the pages in scope and was called again on every scope change — re-reading
  points the live preview had ALREADY translated. Drag +40, switch to "& after",
  and the current page went to +80 while newly-scoped pages got +40; the readout
  still said 40. Switching repeatedly compounded it to +360, after which Reset
  and Escape could no longer restore the originals. The snapshot is now taken
  once, for EVERY page, at mode entry and is never re-derived from a preview;
  pages leaving scope are restored from it rather than left where they were.
* **Page structure is frozen while a move is live.** `moveOrigin` is keyed by
  array index, so selecting, adding, deleting or reordering a page mid-move made
  index `i` stop identifying the captured page — and `commitMove()` recomputes
  its targets from the current `idx`, so the undo record could name a page that
  was never previewed. A reorder could apply one page's captured coordinates to
  another page's strokes. The strip stays visible (it is what makes a move
  judgeable) but stops being operable, and the mutating functions guard
  themselves so a future caller is covered too.
* **A move now redoes.** It was on the undo history but not the redo stack, so
  Redo after undoing a move replayed an unrelated older stroke. `commitMove()`
  also clears the redo branch, as starting a stroke does.

Found by composing two valid actions, not by exercising either alone — every
dimension of this feature passed in isolation. `verify_move.py` is now 67
assertions and covers the transitions; reverting only the origin fix fails 11
of them.

**Still open from that pass:** the action history is global while stroke undo is
page-local (`actionLog` records `'stroke'` with no page identity, but
`undoStroke()` pops from `frame()`). Freezing page structure during a move
removes the acute hazard, but the hybrid model remains and wants a deliberate
choice between page-local history and a fully identified document-global one.
That is a contract decision, not a patch.

### Move reads as a mode (UX pass)

Six changes, all deriving from state that already existed:

* **The bar names the pages.** `#mbWho` shows "Page 3" or "Pages 3-5", written
  by `syncMoveLabel()` from the same `moveTargets()` the transform uses, so the
  preview cannot disagree with the operation. The move bar REPLACES the page
  bar, so entering Move was the exact moment "Page 3 / 7" disappeared.
* **The filmstrip shows scope.** `.frame.in-scope` marks the affected pages —
  better feedback than a text selector and it costs no width in a bar already
  tight at 320px. Deliberately distinct from `.on`, which still means "the page
  you are drawing on"; during a move both are true of the current page.
* **`& after` became language.** "And following", stepping down to "After"
  below 560px. The wider wording cost 23px the bar did not have: it overflowed
  at 320-390 and, since `.pagebar` is `overflow-x: auto`, it did not clip — it
  scrolled and took Done off screen. Caught only because the fit sweep now
  forces the WIDEST label the feature can produce ("Pages 108-162") rather than
  measuring whatever page happens to be selected.
* **Frozen controls speak.** Freezing page structure for correctness left the
  strip visibly inviting taps it would not honour. Tapping now says "Finish or
  cancel the move first" rather than doing nothing.
* **`+ Page` became `+ Duplicate`.** The button already deep-copied the current
  page — draw, duplicate, nudge, duplicate is the animation loop, and the label
  hid it.
* **Undo and redo of a move say so.** A page translation vanishing is far less
  legible than a stroke vanishing, especially across several pages.

### Fourth shared controller: colour selection

`skribl/static/lib/colorselect.js`. Shared: validating a hex, normalising its
case, and marking exactly one preset swatch active. Pad rejected anything that
was not `/^#[0-9a-f]{6}$/` and lower-cased it; **Flip did neither**, so
`setColor('nonsense')` set the pen to a string the canvas cannot paint with, and
`#FF0000` did not match the `#ff0000` swatch it IS.

NOT shared, because the two surfaces are genuinely built differently: Pad shows
the current colour on a custom swatch and an `<input type=color>` and feeds
recents from inside its setter; Flip shows it on the popover trigger and feeds
recents from the custom input and the eyedropper. `apply()` returns
`{hex, matched}` so each surface does its own thing with the result — `matched`
being null is what makes a colour "custom" and worth remembering.

Confirmed shared rather than coincidentally equal: disabling the hex pattern in
the lib alone fails the same three assertions on BOTH surfaces.

**It also moved an existing assertion's target.** `verify_ux.py` checked
flip.js's source for the `!!` coercion that stops
`classList.toggle(name, undefined)` toggling. That logic now lives in the lib,
so the check reads the lib — and gained a second check that neither editor still
carries its own copy. A source-level assertion pointed at the old location would
have passed forever after the code moved, which is the failure mode of that kind
of test.

### The production runtime is pinned (Python 3.12)

`.python-version` carries `3.12`; mirror it with a `PYTHON_VERSION` environment
variable on the Render service. Both, deliberately: the env var is what Render
reads, the file is what a reader of this repository can see without opening a
dashboard.

Why 3.12 and not something newer: `constraints.txt` is a hash-locked cp312
environment, and `harness/RELEASE.md` records the interpreter its numbers were
produced on. Pinning to the tested version makes that evidence describe
production. The alternative — moving to 3.14 — requires regenerating the lock on
that target AND re-running the full aggregate there before any of these
assertions mean anything about the deployment. That is a deliberate upgrade with
its own evidence, not a default.

The environment was also reinstalled from the hashed lock
(`pip install -r constraints.txt --require-hashes`) before the recorded run, so
the evidence describes the LOCKED versions rather than whatever a fresh
`requirements.txt` resolve happened to produce. That caught one drift: alembic
1.19.1 installed against 1.19.0 locked.

`verify_docs.py` now fails if the pin is missing, if the harness runs on a
different interpreter from the pin, or if the lock carries no matching cp tag.

### Stable invariants moved into the schema (revision c7e1a5f04b93)

A NEW revision on top of head `f0a3d81b47e2`. No released migration was
touched; its digest is appended to RELEASED.txt.

* **Foreign key** `skribl_post_media.post_id -> skribl_posts.id`, ON DELETE
  CASCADE. Authorisation for /media/<key> is decided by that table, and the
  package expects a host to touch the same database and possibly build models
  itself — so application validation is not the only thing that can write these
  rows. An association whose post is gone authorises nothing AND makes the
  orphan sweep treat its media as still referenced, which is the leak the sweep
  exists to close. Orphan rows are deleted first, because the constraint cannot
  be created while one violates it; this database has never had a delete path,
  but "in practice there are none" is not a migration strategy.
* **CHECK** on `skribl_rate_events.state`: `pending` or `committed`. A third
  value counts as neither, so it holds no quota slot and is never cleaned up as
  one.

**Deliberately NOT added: a CHECK on `visibility`.** VISIBILITIES is enforced by
the API rather than the database specifically so a host can add its own states,
and `visible_to()` now fails closed on states it does not know with
`set_visibility_policy()` as the way to open them. A CHECK would remove that
extensibility again, at the layer hardest to change. The reviewer offered CHECK
*or* an extensible policy; the policy was chosen, so the CHECK must not follow.

Both constraints are declared in `models.py` as well, or the drift check
reports the migration as ahead of the models — and `create_all()` would build a
table without the constraint authorisation depends on. The assertions insert
violating rows and require the database to refuse them, and delete a post to
confirm the cascade.

### Orphan media has a lifecycle, and the CSRF cookie has a switch

**`storage.sweep_orphans(store, session, older_than_seconds, dry_run)`.** Media
is written BEFORE the transaction recording its association commits: the
association rows are transactional, the object store is not, so a failed or
abandoned commit leaves bytes nothing points at. Content addressing means that
never corrupts valid data — an orphan is unreachable, not wrong — but at scale
it accumulates.

Two deliberate defaults. The grace period exists because an object written
seconds ago may belong to a transaction still in flight; sweeping on the
association table alone would delete the media of a post being created
concurrently, so age is the only thing separating "orphan" from "not finished
yet". And `dry_run` defaults to TRUE because this deletes user data — a
maintenance job that removes things by default is one typo from removing the
wrong ones. Both are asserted, including that a referenced object survives a
real sweep.

`MediaStore` gained `iter_keys()` and `delete_key()`. The base class raises
NotImplementedError on purpose: an object store answers `iter_keys` with a
paginated LIST, and a generic implementation would invite one that loads a
bucket into memory. Do not try to make S3 and SQL one distributed transaction.

**v224 made it a job rather than a plan.** Nothing shipped could invoke any of
this: each deployment had to resolve its own app, find the store the host passed
to `init_skribl`, get a session, and get the argument order right on a function
whose third positional argument deletes user data. `python -m skribl.sweep
--app module:factory` is that entry point — dry by default, `--delete` spelled
out in full, and a second interlock on a grace period under an hour.
`sweep_orphans_report()` returns the same work plus a count for every branch
that DECLINED to delete (foreign namespace, inside grace, referenced, reused
mid-sweep), because otherwise a run that reclaims nothing is indistinguishable
from credentials pointed at the wrong prefix. And a `delete_key` that raises no
longer aborts the run: failures are collected per key and `removed` now means
removed. `verify_sweepjob.py`.

**`SKRIBL_FORCE_SECURE_COOKIES=1`.** The CSRF cookie used `secure=request.is_secure`,
which is only true if Flask can SEE the original scheme. Behind a
TLS-terminating proxy that is a deployment setting, not something this package
can know, so an HTTPS site whose proxy headers are not trusted would ship the
cookie without Secure. The switch lets a deployment state that its public
origin is HTTPS regardless. Off unless asked for.

### The session contract is enforced, not just documented

`create_blueprint(session=None)` accepted None while the package documentation
said a session was required. `models.session()` falls back to the process-wide
binding when an app has none of its own, so a second application initialised
WITHOUT a session could reach whichever database the last app to pass one had
bound — the cross-application coupling the per-app `app.extensions` storage was
written to end, reached through the door left open for it.

Demonstrated first: `init_skribl(Flask("no_session_app"))` raised nothing at
all. It now raises at startup, naming what the host has to pass. A blueprint
that genuinely never queries is built with `session=False`, so the absence is
deliberate rather than forgotten.

### LocalDiskStore no longer stores metadata beside the object

`put_bytes()` renamed the body into place and THEN wrote a `<key>.type`
sidecar. Two writes, not atomic together: a crash in between left the media
present without its type, and permanently, because every later call begins
`if os.path.exists(path): return` — nothing repaired it — so `read()` served
`application/octet-stream` for that object forever. Two writers of identical
bytes could also race over the sidecar.

Reproduced before fixing: store a wav, delete the sidecar, and the type came
back `application/octet-stream`; re-storing the identical bytes did not repair
it. Three assertions failed.

The content type is now DERIVED from the key's extension. That is not a guess:
`key_for()` builds the key from the already-validated content type, and
`_KEY_RE` rejects anything that is not a hex digest plus a known extension
before it can reach the filesystem. One file, one atomic rename, nothing to
repair, and no second write to race over.

A side effect worth having: aliases normalise. `audio/wav`, `audio/x-wav` and
`audio/wave` are one object served as `audio/wav`, rather than as whichever
spelling the first uploader happened to send. Any `.type` file left by an older
build is ignored, so there is no migration.

### Unknown visibility states now fail closed

`SkriblPost.visible_to()` used to read "anything that is not private is
readable". `VISIBILITIES` is enforced by the API rather than a database
constraint SPECIFICALLY so a host can add its own states without a Skribl
migration — the model comment invites it — so a host adding `draft`,
`moderated`, `blocked` or `scheduled` would have created posts hidden from the
feed and readable by anyone holding the id. A listing filter pretending to be
an access control: the exact mistake `visible_to()` was written to end, one
layer up. Demonstrated before it was fixed — five assertions failed.

Now: `public` and `unlisted` are readable, and `private` **and every state this
package does not define** are author-only.

An extensible vocabulary needs an extensible policy, so refusal is not a dead
end:

    skribl.set_visibility_policy(lambda post, viewer_id: ...)

Returning `None` defers to the built-in rules, so a host only describes the
states it added. It can open its own states AND close built-in ones, which is
what moderation needs. A non-callable is refused at install time rather than
exploding mid-request. Clearing it restores the defaults.

`routes.py`'s media authorization query changed with it, from
`visibility != "private"` to an allowlist. The two must agree: a query saying
"anything but private" would have handed out the media of a `draft` post while
the post itself was refused — which is how externalised media routed around
visibility once before.

### Slider positioning consolidated — and two of my own claims corrected

`app.js` and `flip.js` no longer carry their own `attachSegSlider` /
`positionSegSlider`; both delegate to `lib/segslider.js`, which gained
`attach()` and `placeAttached()`.

**"Three implementations of the same thing" was wrong.** `place()` positions an
EXISTING markup pill at a fixed 3px offset; `attach()` CREATES a pill for
JS-built groups (the zoom magnifier and focus bars, which are not `.seg` and do
not share its padding) and positions relative to the first button. Different
groups, different offset origin. They must not be collapsed into one. The real
duplication was only between the two editor copies, and a token-level
comparison showed those differed in three cosmetic ways: `Array.prototype.slice`
against `[].slice`, a variable named `activeBtn` against `a`, and a trailing
comma.

**"The same control ends up with a different pill element by accident" was also
wrong.** `_skribl_draw_drawer.html` emits the pill span
`{% if kind == 'flip' %}` — Flip gets a markup span positioned by
`positionSmoothSeg`, Pad gets a div created by `attachSegSlider`. That is a
deliberate conditional, not drift. A first pass reported it as a defect.

The merge is confirmed live rather than assumed: widening attached pills by
20px in the lib now fails the placement assertion, where the same perturbation
before the merge changed nothing. It fails on Pad only — Flip's smoothSeg takes
the markup-span path — which is exactly the asymmetry that template conditional
creates, and a useful check that the assertion is reading the real code path.

### Pill placement is measured before the sliders are merged

`verify_parity.py` now measures every segmented pill's RENDERED rect against its
RENDERED active button, on both surfaces. Written before touching the three
slider implementations, because the risk there is a pill landing in the wrong
place and nothing else in the harness would notice.

Four things had to be right, and each produced a false result first:

* **Open panels by clicking their real opener**, not by setting `hidden=false`.
  A panel revealed by fiat has a pill that was never placed: it measured 0 wide
  on Flip and Pad's segs measured 0 tall, which looked like a 35px misalignment
  and was entirely an artifact. An earlier pass nearly reported it as a bug.
* **Open idempotently** — clicking an opener toggles.
* **Wait for placement** — positioning runs through ResizeObserver and
  MutationObserver, so a same-tick measurement reads zero.
* **Measure `#smoothSeg` BEFORE opening the menu**, which closes the draw
  drawer that contains it. Measuring after returned a null indistinguishable
  from a positioning failure.

**The mutation test found something the assertions could not.** Perturbing
`lib/segslider.js` changed nothing: these segs are positioned by the per-file
`attachSegSlider` copies in app.js and flip.js, NOT by the lib, which is used
only for other controls. Perturbing the code that actually runs — widening every
pill by 20px — fails the assertion with `dWidth: 19.7` on both surfaces. Any
consolidation of the three implementations now has a net under it, and the
mutation is also proof of which implementation is live.

### Third shared controller: smoothing — and the next target found

`skribl/static/lib/smoothing.js`. Small, and worth doing: the level-to-alpha
mapping (`off 1`, `low 0.5`, `high 0.25`) was three magic numbers written out
twice and asserted nowhere, so both surfaces could have drifted to different
stabilizer strengths with every existing assertion still passing. There is now
one that walks every level on both surfaces and compares the resulting alpha.

Pill repositioning is injected rather than shared, because of what looking for
it turned up: **slider positioning exists three times in this codebase** —
`attachSegSlider` in `app.js`, a second `attachSegSlider` in `flip.js`, and
`lib/segslider.js`, which both files also use for other controls — plus Flip's
bespoke `positionSmoothSeg()` for this one segment. That is the next extraction,
and it is a bigger one than it looks: the two `attachSegSlider` copies inject a
`div.seg-slider` while the shared partial supplies a `span.seg-slider`, so the
same control ends up with a different pill element depending on which surface
rendered it. Consolidating them needs its own before-and-after assertions, not
a quick merge.

### Second shared controller: the eyedropper, and one path instead of two

`skribl/static/lib/eyedropper.js` owns arming, the button's class and
`aria-pressed`, the canvas cursor, Escape and the one-shot semantics. Reading
the pixel stays per-surface: Pad and Flip genuinely differ on context, DPR and
what a transparent pixel means, so `onSample` is injected.

**Pad's native `window.EyeDropper` branch was DELETED.** It was not an
alternative to tap-to-sample, it was an extra: Safari, Firefox and every browser
on iOS have no EyeDropper, so the in-app path had to exist regardless. Keeping
both meant two implementations forever and two different experiences behind one
button depending on the browser. It was also the wrong semantics — the native
picker samples anything on screen, including other applications, when the ask is
"the colour of that part of my drawing" — and an OS dialog cannot be driven by
the harness, so the path most desktop users took was the one no assertion could
reach. Deleting it removes a path rather than adding one. The cost is that
desktop Chrome loses screen-wide sampling; if that is wanted back it belongs in
this file, once, not in one editor only.

Both surfaces now also announce the armed state with `aria-pressed`, which
neither did before — a class alone says nothing to a screen reader.

**Two of the assertions written for this were wrong, in instructive ways.**
The first clicked the drawer opener unconditionally, which TOGGLES: a drawer
left open by an earlier section was closed by the step meant to open it, and it
surfaced as "element is not visible" on a button that plainly existed. Opening
is now conditional on the panel not already being shown. The second asserted
that disarming "drops the crosshair" — but Pad's IDLE canvas cursor is a
crosshair, because it is a drawing surface. The parity statement is that each
surface returns to its OWN baseline, captured before arming, not that both end
up at the same literal value.

### First shared controller extracted: recent colours

`skribl/static/lib/recentcolors.js`. Both editors now call one implementation;
`addRecent()` and `renderRecent()` remain in each file as thin wrappers so no
call site had to move, and `recentColors` is kept in step through an `onChange`
callback because several call sites read that variable directly.

**Reading the two implementations side by side found drift the parity suite had
not reached**, because the assertions written first did not observe it:

* Pad validated `/^#[0-9a-f]{6}$/` and lower-cased; Flip did neither, so
  `#AABBCC` and `#aabbcc` could both be stored, and an unvalidated string
  rendered as a transparent swatch that set the pen to nothing.
* Pad gave each swatch an `aria-label`; Flip set only `title`, which is not an
  accessible name and does nothing at all on a touch device.

Neither was deliberate. Both are now assertions that failed before the
extraction and pass after — which is the order that makes an extraction
provable rather than merely finished.

**What is deliberately NOT shared:** what happens when a swatch is picked. Pad
sets the pen and leaves its bottom drawer open; Flip sets the pen and closes its
popover, which sits over the canvas. That is layout, injected as a callback.
Extract behaviour, not layout — Pad and Flip are meant to feel different.

**Verified as genuinely shared, not coincidentally equal:** changing `LIMIT`
from 6 to 4 in the lib alone, in a scratch copy, moved BOTH surfaces to 4. Two
implementations that happen to agree would not have done that, and that is the
property the whole refactor is for.

**A vacuous assertion was caught while writing this.** The check that neither
surface stores an invalid colour originally compared list LENGTH — but once the
list is full at six, adding three invalid entries leaves the length unchanged
whether they were rejected or stored. It now checks contents.

### The first full aggregate run

`harness/RELEASE.md` is generated by `harness/release_run.py` and is the answer
to "what was tested, on which tree". Every suite reported on one frozen tree,
1510 assertions, 2 declared skips (`verify_mp4.py` — headless Chromium has
WebCodecs but no H.264 profile; `verify_postgres.py` — no PostgreSQL client).
The tree hash is computed before batch 1 and RE-VERIFIED before each of the
eleven batches, so a source edit mid-run aborts instead of being averaged into
the result.

Point other documents at that file rather than repeating its numbers. Volatile
release facts are generated here precisely because hand-typed ones drift, which
is how a stale hash in START-HERE.md once made an external reviewer distrust
provenance that was actually sound.

**The first run of it failed, and the failure was in the reporting, not the
code.** It reported 36/38 with `verify_mp4.py` and `verify_postgres.py`
"reporting nothing". They had reported: `run_harness.sh` printed
`verify_mp4.py: SKIPPED (0 assertions) — ...` with the reason. The parser
required `(\w+) — ` for the status field and the `(0 assertions)` parenthetical
broke the match, so a DECLARED skip with a stated cause was recorded as
unexplained silence — the exact failure the batch diagnostics exist to prevent,
committed by the code that writes them. Skips are now matched on a `SKIP` prefix
and separated from failures.

Note also that background processes survive between tool invocations in this
sandbox; the aggregate had previously been described as impossible to run here
on the assumption that they do not. Test the assumption before repeating it.

### Parity between the two editors is now testable

`harness/verify_parity.py` (42 assertions) loads BOTH surfaces and checks they
agree about the controls they share. It exists because every other suite drives
one surface — `verify_review`'s 277 assertions never load Pad, `verify_ux` hits
Flip twelve times against Pad's two — so drift between the duplicated
controllers failed nothing.

It is built on a CONTROL MAP rather than an id diff, because the same control
has different ids on each surface: undo is `#undoBtn` on Pad and `#undo` on
Flip, brush size is `#brushSizeRange` against `#size`, photo opens from
`#imageOpenBtn` against `#imageBtn`. An id-set comparison reports that noise and
misses the real divergence. The map names each control once and records where it
lives on both surfaces — which makes it the extraction plan as well: every row
is a controller boundary, and this suite is the acceptance test for moving one.

Rows with a `None` selector are DELIBERATE differences (the filmstrip is Flip
only; the empty-canvas hint is Pad only). Pad and Flip should not converge —
Pad is meant to be immediate, Flip is an animation tool — so the value is that
differences are declared rather than accidental.

**Behaviour parity, not just structure.** The suite drives the same user action
on both surfaces and compares the OUTCOME: the shared draw drawer opens, exactly
one colour and one smoothing option read as selected (the
`classList.toggle(name, undefined)` bug once left two selected at once), recent
colours keep the same cap, order and de-duplication, the brush readout tracks
its input, and the eyedropper arms tap-to-sample. That is what an extraction has
to preserve, and structure parity alone would not notice losing any of it.

**Media parity uses real bytes.** The photo and music controllers are the
largest duplicated pair (350 and 131 references in app.js against 83 and 97 in
flip.js), so they are what an extraction hurts most if unguarded. The suite
generates a real 8x8 PNG and a real one-second 440Hz WAV in Python — no binary
fixtures in the tree — uploads them to BOTH surfaces and compares what happens:
tab markers, fit choices, opacity range, the trim handles' reported start and
end (so both read the same duration from the same file), and a nudge moving the
trim edge by the same amount. The waveform check reads PIXELS rather than state,
because an empty canvas beside a loaded track is exactly what a state assertion
misses.

**The suite was mutation-tested, not merely run.** Breaking ONE surface in a
scratch copy — Flip's brush minimum 2 to 3, Flip's recent-colour cap 6 to 4 —
produced two failures naming the exact divergence. A first mutation attempt
silently did not apply because the string did not match, which proves nothing
either way; that was checked before drawing a conclusion.

**A diagnostic worth knowing:** a parity assertion that is simply WRONG fails
symmetrically — 0 on Pad and 0 on Flip. Real drift fails asymmetrically. Four
first-run failures all read 0/0 and were bad selectors, not divergence.

**Declared difference found while writing it:** Pad uses the browser's native
`window.EyeDropper` when present and returns early, so it shows no armed state;
Flip always uses the in-app tap-to-sample path. On iOS Safari there is no native
picker, so both fall back — and that shared path is what most phone users get.
The suite deletes `window.EyeDropper` before testing it, because comparing an OS
dialog against an in-app mode proves nothing. Whether Flip should adopt the
native picker where available is an open product question.

**Found on the first run:** the brush size range differs by surface, Pad 1-30
default 5 against Flip 2-34 default 7. `_skribl_draw_drawer.html` records THAT
they differ but not WHY. Pinned as characterization so it cannot drift further;
if the two should match, that assertion is where the decision gets made.

### Still open

**The loop fine-tune magnifier has no CSS.** `app.js` builds `.zoom-mag-bar`,
`.zoom-mag-group` and `.zoom-mag-btn`, and those class names appear in exactly
one rule across both stylesheets (`touch-action` in flip.css). Same shape as the
export sheet's Size/Pages. `attachSegSlider` also points a `.seg-slider` at a
group with no `position: relative`, which is what painted a purple bar down
Pad's canvas menu.

**The export sheet's segs are unmeasured.** `#exportSizeSeg` and
`#exportLoopsSeg` never rendered in the harness used here, so they have no
`--seg-h` and keep their inherited height.

**`START-HERE.md` in this archive is the v175 copy.** Its suite count and file
count are four versions stale, and it points at `docs/v175-client.patch`. (The
counts are deliberately not repeated here: `verify_docs.py` scans for
hand-typed "N suites" claims and cannot tell a quotation of a stale number from
a stale number, which is the correct trade — it caught this paragraph.)
`verify_docs.py` checks
README.md, harness/README.md, docs/HANDOFF.md and ARCHIVE-README.md — not
START-HERE.md, which is the one document a new session reads first. Adding it to
that check, plus an assertion that every path named in the docs exists, closes
both holes.


* `app.js` is large and still serves both the editor and the player (measure it
  with `wc -l` rather than trusting a figure here — this line has quoted a stale
  one twice). A
  split was attempted and REVERTED; see docs/REFACTOR-v132.md for why the
  regex-based call graph was the wrong tool and what to use instead.
* The S3 media backend is a subclass hook, not an implementation.
* Multi-take has no data model, by design — it is a product decision first.
