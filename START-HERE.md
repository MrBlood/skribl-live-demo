# START HERE — Skribl session primer

## Next session: read this block first

    result       see harness/RELEASE.md — generated, never typed here
    tree hash    see harness/RELEASE.md — generated, never typed here
    files        see SHA256SUMS — the command below prints the count

Nothing in this block is a number, deliberately. It used to carry an assertion
total, a suite count, a skip count and a file count, and carried all four
unchanged through three builds that changed every one of them. `verify_docs.py`
caught the suite count only because that one happened to be checked against the
directory listing. A number typed here is a number that goes stale silently.

Verify before believing anything in prose, including this file:

These commands are run in the UNPACKED RELEASE, not in a git checkout —
`SHA256SUMS` is written by `harness/package.py` into the tarball and is not a
tracked file, so in a clone the first two lines have nothing to read. From a
checkout, `harness/RELEASE.md` and `release_run.tree_hash()` are the two that
still answer.

    cd skribl-v*                                    # the name derives from SKRIBL_VERSION
    grep -Ec '^[0-9a-f]{64} ' SHA256SUMS            # N: the manifest's own entry count
    sha256sum -c SHA256SUMS | grep -c ': OK'        # must equal N
    grep -m1 'tree hash' harness/RELEASE.md
    python3 -c "import sys;sys.path.insert(0,'harness');import release_run as r;print(r.tree_hash())"

**What a visitor downloads on a shared link — RUN IT, do not read it:**

    ./harness/run_harness.sh verify_player_isolation.py

Its last assertion prints the whole payload broken down — JS, HTML and CSS
separately, their sum, and the gzipped figure — and the suite fails if any part
grows past its ratchet. **The numbers are deliberately not repeated here.** This
block used to carry nine of them across two tables, every one measured at v199,
and they were still sitting here unchanged dozens of releases later describing a
player that had shrunk under all of them. That is the same failure the paragraph
above this one warns about, committed fifteen lines after warning about it.

One of those numbers is worth knowing as a SHAPE rather than a value: the
gzipped "on the wire" figure is roughly a quarter of the source total, and must
never be quoted as "the player's JavaScript" — the suite says so at the
assertion itself.

`skribl/jsstrip.py` removes comments from the RESPONSE — the files on disk keep
every word, which is the only reason this was allowed at all — and
`harness/tools/cssgraph.py` classifies rules inside a media block instead of
keeping the whole block whenever one rule matched. Neither moved a byte of
source.
`verify_jsstrip.py` is the gate on the first (Chromium compiles and evaluates
every case; the lexer checking its own output proves nothing) and
`verify_cssplit.py` on the second (eleven scenes, pixel-identical).

## Invariants, and what enforces each one

These outlived the releases that produced them. Each line is a rule a change
can break, followed by the suite that would catch it — **checked by grep, not
recalled.** An invariant with no enforcer is marked as such, because "we all
know that" is how a rule stops being true.

These rows replaced the "Closed in vNNN" narratives (708 lines, v282) and then
the whole HISTORICAL NARRATIVE band (1,370 lines, v283). The reasoning behind
each release lives in `DECISIONS.md`; the *history* lives in git. What has to be
here is the rule you can break tomorrow.

| invariant | enforced by |
|---|---|
| A route flushes; it never commits the shared session. | `verify_txcontract.py` (AST over every module, exemptions named per function) |
| Undo stores a DRAWING, not a screenshot — replay reconstructs from strokes. | `verify_move.py`, `verify_stamps.py`, `verify_liquify.py` |
| An anonymous post is revoked by a CAPABILITY, never by an account. | `verify_deletion.py`, `verify_posted.py` |
| Possess the id and the key → revoke through the product, whatever this browser remembers. | `verify_posted.py` |
| A 404 from DELETE means UNKNOWN. The client must not turn it into success. | `verify_posted.py` |
| The player carries no editor-only module. | `verify_player_isolation.py` |
| Your hand (`/skribl-pad?letters=1`) keeps no Pad draft and leaves the Pad's brush and mirror as they were; a letter changed (put back as ink, fitted to the screen; the eraser cuts its points, every point left keeping its time) replaces the old one only on Done; a posted set, whole or not, reads back to its letters by the one layout rule `editor_letters.js` and `harness/tools/letterfont.py` share. | `verify_letters.py` |
| Text is ink, not type: nothing is drawn or recorded until Write it; the words go in as ordinary strokes, each point at the time the plan gave it on the editor's clock, forward only; one Undo takes the line back; Mirror never copies them. One module (`lib/textwrite.js`) for both editors. INSIDE A POST (compose mode) MAKE YOURS AND EDIT YOUR HAND GO NOWHERE (the owner's "All yes", Nov 19): Your hand opens in a layer OVER the editor (`lib/handover.js`, `handover.css`, both editors), so the editor's address and its drawing are the same before, under and after, its button still Add; Your hand, told it is over one (`?over=1`, a face's Pad `over=face`), says where the drawing is, leaves out Post your letters, and every way out of it asks that editor to close the layer (one message, taken only from the frame it opened); the layer glides up and down, and fades where it sits under Reduce Motion, past the editors' own rule that stops every transition there. On the editors' own pages the page still goes to Your hand, its draft keeping the drawing. | `verify_text.py` (23 for the layer), `verify_composer.py` (10) |
| The player's JS stays under its ratchet, measured on what is SERVED (comments stripped), not what is on disk. | `verify_jsstrip.py`, `verify_player_isolation.py` |
| `[hidden]` is honoured on every control that uses it. | `verify_layout.py`, `verify_help.py`, `verify_move.py` |
| No readable text uses a token that fails WCAG AA. | `verify_a11ypages.py` |
| WAVE's error rules find nothing on any page, fresh or filled: an icon is hidden or named on the svg itself, every field and label says something, no heading is empty, no ARIA reference points at nothing. | `verify_a11ypages.py` (A11Y 19) |
| No words at 10px or under, WAVE's very small text, on any page or where the five that drew them show: Flip's tool tray's labels, the draw drawer's Recent, the shape card's knobs, How it works' tip counts and the music trim's time bubbles are 12px, and the bubbles stay over the track. Flip's page strip's numbers and hold badges are in too, since the owner picked how they fit (one ⋯ per page on a phone). The LINK PAGE has nothing under 12px, at rest, playing or with More open ("made with" was 11), and the line under the Library's list has its links at 12px, empty and with posts. | `verify_a11ypages.py` (A11Y 20), `verify_loopui.py`, `verify_linkpage.py`, `verify_library.py` |
| A token that cannot pass AA must be USED somewhere the requirement does not reach, or not exist. | `verify_a11ypages.py` |
| Every `aria-modal` surface takes focus, keeps Tab in, closes on Escape and hands focus back: through `SkriblModal`, or, for Your hand's layer over a compose editor (a frame, so it keeps the same promises its own way, `lib/handover.js`). The population is generated from the DOM (the editors' own pages, and the compose pages for what only they render) and the JS source, not listed. **A change that adds a dialog runs this suite**: #1004 did not, and main was red for a night. | `verify_a11y.py`, `verify_text.py` |
| Every id on a rendered page is unique — `getElementById` and `url(#…)` both take the first match. | `verify_a11y.py` |
| No page loads a `lib/` module nothing on that page reads. | `verify_surfaces.py` |
| No stylesheet keeps a rule-set whose every selector is unmatched. | `verify_surfaces.py` |
| Every tip in How it works is claimed by a check that TRIES it — a named check in another suite, or a probe that drives the page's own controls — and every ⋯ menu row and tool is named in the sheet. A new feature ships with its tip and its proof, or the seal is red. | `verify_helpclaims.py` |
| Every screen recording How it works places (the book's pages, the button cards, Ask's answers) shows whole: the clip at its own ratio (`data-ratio`, from the shape `make_help_clips.py` cut it to) inside its own outline, a phone's screen in a frame that holds the tallest and a tool's 4:3 (Flip's tray) across the card's stage; the book's picture is one height on every page. | `verify_book.py` (section 7, every place by name, painted to the clip's edges and corners) |
| The Photo \| Music tabs and the open media drawer are ONE card on both editors, shown by CSS whenever a media drawer is open. A drawer's file row is the drop area until a file is added, then the file; its bin asks before it removes, and a drop anywhere on the card reaches the open drawer's input only if it is the right kind of file. | `verify_parity.py`, `verify_a11y.py` (A11Y 2b, 10c) |
| Every route the blueprint registers is named in at least one document. | `verify_docs.py` |
| Every host seam `create_blueprint()` accepts is documented in `docs/INTEGRATION.md`. | `verify_docs.py` (reflection over the signature) |
| A host's brand reaches Skribl's editors through one seam (`brand_resolver`, `skribl/brand.py`), per request: its mark in the signature's slot (the hand's scale, the part of its box past 30 units hung below the line, the signature's width kept, so nothing in the header moves), its label naming the lockup and the page's heading, and a first-open hello of its own remembered by a key of its own. An answer of nothing is the Pad and Flip byte for byte as Skribl's own; a wrong answer raises on the first page that asks; nothing under `skribl/` names a host. | `verify_hostseams.py` (THE HOST'S BRAND) |
| A host says where the Gallery's cards open through one seam (`card_url`, `skribl/models.py`), per request: an address with `__ID__`, opened from anywhere on a card that is the card's own (a drag or a selection opens nothing; Ctrl, ⌘ or the middle button opens a new tab), the card's title a link to it, its ⋯ → Open going there. An answer of nothing is Skribl's own Gallery byte for byte; a wrong answer raises on the first page that asks; nothing under `skribl/` names a host. On the Skribl site every card opens its post, Home's included. | `verify_seam.py` (WHERE A CARD OPENS), `verify_hostseams.py`, `verify_socialposts.py` (12) |
| Every `SKRIBL_*` the code reads is named in a doc or `.env.example`. | `verify_docs.py` |
| No document hand-types a tree hash or an assertion count outside the generated stanza. | `verify_docs.py` |
| The generated doc tables match their source. | `verify_docs.py` → `gen_docs.py --check` |
| A skipped suite contributes ZERO assertions and is not evidence of coverage. | `run_harness.sh` emits it; `stamp_docs.py` writes it into every stanza |
| The release run must be the LAST harness invocation — anything after it rewrites `LAST-RUN.txt`. | `verify_docs.py` (RELEASE.md/LAST-RUN.txt agreement), and the guard in `stamp_docs.py` |
| A run that did not walk every suite on disk does not stamp the generated stanzas. A one-suite calibration run -- reddened on purpose, as this project requires -- twice wrote "RUN NOT GREEN" into a document and twice reached a commit. | `verify_docs.py` (the predicate driven with synthetic records: whole tree, one suite, a release batch, and an empty tree) |
| Every suite on disk appears in exactly one `release_run.py` batch. | `release_run.py` refuses to start otherwise |
| The assertion output format is a contract `run_harness.sh` parses. | `harness/assertions.py` self-test, run by `verify_docs.py` |
| Every tool emits ORDINARY STROKE POINTS — a point carries no field outside `{x, y, color, size, t, start, erase}`. A shape primitive or brush id would be a schema change every existing post has to survive. | `verify_tools.py`, `verify_inline.py`, `verify_tween.py`, `verify_inbetween.py` |
| Smear and Tween (Motion Smear and the in-between) are two features on one pairing. The smear integrates the whole path between two poses as a span of pages; the in-between emits ONE pose partway and costs about a source page. Both pair strokes BY SHAPE (`tweenMatch`, since v296), so a pose can be redrawn in any order, and a stroke with no partner is drawn once. | `verify_tween.py` (the span, the falloff, the per-page cap, pairing by shape in another stroke order), `verify_inbetween.py` (phase, the similarity fit, the Help saying strokes pair by shape) |
| Replay joins consecutive points, so any group holding two distant places draws a line across the canvas. Flip refuses the share outright when `strokeGroups` does not account for every point. | `verify_strokegroups.py` |
| `pauseMode` is serialized and the preview's speed is not — a setting that changes what the drawing IS travels with it; one that changes how you review it does not. The one speed a post carries is `playSpeed`, the author's pick of where a VIEWER STARTS ('auto', 'drawn', 'fit' or ¼× to 16×); the server refuses anything else, and a post without it plays as drawn. | `verify_tools.py`, `verify_replayspeed.py` |
| The Pad's preview and the shared player offer one set of speeds, say them in one line ("Drawn in 47 min · watching at 8×") and work out Fit one way, from one module (`lib/replayline.js`), which the in-post player's line under a post loads too; the player still writes out the start rule for a page that plays posts without the line (the profile's stage). A speed picked mid-play re-anchors the clock: the drawing carries on from where it was. | `verify_replayspeed.py` |
| "Drawn in" and the clock under the track are the ARTIST's time (every positive gap, uncapped); when the replay skips a tenth or more of it, the line says "long pauses skipped". | `verify_replayspeed.py` |
| The music follows the drawing's speed between ½× and 2× and is a bed at its own rate outside them (a 16× clip is noise). | `verify_replayspeed.py` |
| The speed choice opens at its ends wherever it shows (the Pad's line and its desk pill, Tune, the link page, and the post's box, which keeps a copy of its own): an end speed sits no nearer the pill's rounded edge than two speeds sit to each other, and never inside the inner half of the curve, in three faces (a word is centred in a 44px or shared speed, so its place follows the face). Nothing runs out of the pill; Tune's stays inside its row; a line's may reach past the line, never nearer the screen's edge than a twentieth of the screen. | `verify_replayspeed.py` (THE PILL'S ENDS) |
| The Pad's Repeat sits beside the speed (the desk pill, and the line under the drawing between the speed and full screen), off to start and remembered as the speed is. On, Play goes round until it is stopped, each round from the first point with no frame held at the turn, its music begun again from the loop's start, and playing on every frame between; turned off mid-round, that round is the last; Stop leaves it on. "Play with my drawing" follows. The music ends by the drawing's own clock, so a scrub back never stops it early. In full screen it wears the speed's glass, and a pressed full screen's light while on. Posts keep their own loop button, off to start as this one is since Nov 15; Flip has no Repeat. | `verify_padrepeat.py` |
| Once a drawing has POSTED, the Post sheet says so in a band of the brand's purple (Blooby's jump, "Posted!", the line each editor says) and the form folds away; the card under it is the post as people will see it: the drawing in its own shape, matted on the card, as big as the sheet has room for up to half the screen with all of the sheet on the screen (a window too short keeps it at 160px and scrolls), drawing itself in the in-post player on its own ground (never its finished picture first), the Pad's once in about three seconds, a Flip's twice round to its first page; its title, and two lines of its caption with a "more". A press inside the sheet never closes it, even on a button that rewrites its words as it is pressed. The sheet glides and the parts rise in; under Reduce Motion nothing moves and the card is the picture. Make another starts a new drawing with New Skribl's Undo, and Back to the site shows only when the host named its home (`create_blueprint(home_url, home_label)`, refused at startup unless an http(s) address or a path). A reason a post did not go sits in a card right above Try again. Compose mode renders none of it. | `verify_postmoment.py`, `verify_identity.py` (his paint), `verify_contrast.py` (the posted sheet and the reason card) |
| On a post this browser made, the link page's button says Back to Pad (Back to Flip on a Flip) and is the way back: a step back when the editor is the page just left, else the editor itself; on anyone else's it asks them to make their own. | `verify_linkpage.py` |
| The LINK PAGE has a way back to the site only when the host named its home: one link at the top left, "‹" and the site's name, to that address in the whole tab, a 44px tap over nothing (on a phone the page keeps its height clear), covered by the drawing's own full screen. Standalone there is none. The caption is a size up in the page's ink (17px, 14 on a phone on its side) under a title of 21px, both 7:1. | `verify_linkpage.py`, `verify_player_isolation.py` (the CSS it costs) |
| A Pad post's LINK PAGE shows the post's own picture where the canvas will be before its data has come (its size, title, caption and line come with the page), cropped to the drawing and wearing the frame's own edge, and the box never moves when the drawing arrives. The ink is laid under it in slices, each shown, a frame's length steering the next, and pixel for pixel what one call lays; the picture fades once the ink is whole (at once under Reduce Motion), and goes the moment Play or a seek takes the canvas. A Flip's page has none of it. | `verify_firstlook.py` |
| The CAPTION is where people look: in the gallery, under the drawing at rest, two lines of it and a "more" exactly where it runs longer, asked again when the width changes; "more" glides the rest open and "less" back, the words whole while the box shrinks (Reduce Motion just changes); no caption mark in the head; two cards side by side end at their own heights, the drawings level. In the Library, in full under the stage's title and one line on each row. On the LINK PAGE too, two lines and a "more", so a long caption never makes the drawing smaller: "more" opens the rest in place and the page grows under it, the drawing at its size. And on the Posted! card, where the open caption scrolls the sheet rather than taking the drawing's room. One copy of the two lines and their "more" for every surface (`lib/capmore.js`). The posted list keeps it, and a row kept before learns it once from `/api/skribls/meta`. Wherever a post's title and caption show (the link page, the gallery, the Library, the Posted! card), a word too long for its line breaks to stay inside, and nothing scrolls sideways. | `verify_captions.py`, `verify_gallery.py` (the card census, more and less, the close), `verify_linkpage.py` (the link page's two lines), `verify_postmoment.py` (the Posted! card's) |
| The document has TWO ceilings — points and pages — and every door that adds a page refuses at either one BEFORE the button: Duplicate, Blank, Paste, Tween, Smear. Pages first, because a smear costs two and 200 arrives before the points do. The message names which. | `verify_sharedrules.py` (each client cap equals the server's), `verify_tween.py` (every door, at the cap and one under it) |
| A run of ONE alpha that is not one path is composited once, never walked, on both surfaces. `uniformRun` asks "one path?"; compositing asks "one alpha?" — different questions. | `verify_smudgeblur.py` (Flip: the vertex ripple), `verify_beading.py` (player: the ceiling) |
| Field runs and rgba() strokes share ONE layer budget, counted by one predicate in the shared module, on both surfaces. Two counts of 24 is a frame of 48 composites. | `verify_smudgeblur.py`, `verify_beading.py` (both sides of the boundary) |
| The layer is never paid for on a move of a live field drag; the page the artist is left with is the correct one. | `verify_smudgeblur.py` (mechanism, not a clock: mid-drag compounds, after does not) |
| With a mirror live, a layered stroke's reflection survives the composite. | `verify_smudgeblur.py` |
| A generated page rebuilt from a draft comes back the weight it was MADE at: the recipe carries it, the live setting does not. | `verify_tween.py` |
| `mix()` preserves the ink's alpha in every spelling it arrives in, and returns it in the spelling that keeps it off the layer budget. | `verify_smudgeblur.py` |
| COMPOSE MODE PUBLISHES NOTHING. "Add to post" hands the payload to the host; only the host publishes. | `verify_compose.py` |
| The compose handshake targets a specific origin, never `'*'`. | `verify_compose.py` |
| A host must limit its own compose view — Skribl's limiter cannot follow the payload into somebody else's composer. | `verify_compose.py` |
| COMPOSING, NO LINK IN THE ⋯ MENU LEAVES THE EDITOR WITHOUT ASKING. Compose keeps no draft, so a link out of the host's frame takes the drawing on the canvas with it: inside a post the menu has no Library and no Public gallery (the editors' own pages keep both), and the switch to the other editor asks first. | `verify_compose.py` (every painted link in the menu followed with a drawing on the canvas, Pad and Flip) |
| The Pad's Undo and Redo put a drawing the canvas held a moment ago back from its kept copy, every pixel, without painting it again: three copies, reused, each only for its own points, base, size and stroke layers. Anything else repaints as before. The copies are for a busy drawing (from 4,000 points, as Flip's): a light one keeps none, and a stroke laid on one drops what a busier drawing left. | `verify_undofast.py` |
| Flip's Undo and Redo on a busy page lay the page from a kept copy, known by its ink's content, and its tile from a kept picture: every pixel what a full repaint shows. A copy is only ever taken of the page at rest, and a new size drops them all. | `verify_undofast.py` |
| The Pad OPENS a long drawing (past 20,000 points, from a file or a reload's autosave) in one paint, the canvas grown to its screen before it rather than after: laid a slice a frame and shown as it goes, pixel for pixel what one call lays, no task a third of the one call. The first press or key on the page finishes it at once, before anything it does. A shorter drawing paints in one call as before, and the Pad's own player never in slices. | `verify_padopen.py` |
| Flip OPENS a long Flip (its pictures past 20,000 points) with every tile in place at once, the page you are on painted and the rest showing their ground; the other pictures come a few a frame, nearest first, each pixel for pixel what one call paints, no task half the one call. A tap on a tile not yet painted paints it at once; a short Flip paints whole as before; the opened Flip's draft is written in a task of its own. | `verify_flipopen.py` |
| A page's tile is painted over the backdrop as it is now and framed at the canvas's size: a new photo, its strength, the photo switched off or a new size reach every tile. | `verify_pages.py` |
| When the drawing stops, the music stops. | `verify_audiosession.py`, `verify_inline.py` |
| Play, Stop and the sound switch never click: each glides over 5ms (`lib/audioloop.js` glide, fadeIn and fadeOut; a post's box carries its own copy of the three), in both editors, on the link page and in a post's box. Measured on what reaches the speakers. | `verify_soundfade.py` |
| The music drawer's doors only show and hide, one at a time: opening, swapping and closing keep the loop. Skribl's pick is for a song just chosen; a song a draft brings back keeps the draft's loop. What a smooth restart folds off the loop is counted wherever the drawer says a length or fits the drawing, and the one line under the timeline keeps its height whatever it says. | `verify_musicdoors.py` |
| Every change to the loop is a step the music drawer's own Undo and Redo take back and again, exactly (its ends, its restart, its cut, its beat): one per drag however far and per held slider, a settle with its glide, a change made mid-glide its own step from where the settle was going. The zoom, the taller box, the magnet and Lock the length are not steps, nor is what Skribl does on its own; a new song starts a new history, and a change after an Undo drops what Redo held. The bin's note brings a song back as it was, its loop and its history with it (on the Pad its bytes back in the draft's store). An end reaches 32px either side of its line and 26px below its tab, keeps its distance from the finger as it moves, and the nearer end takes a press both reach; the whole song's line takes a press on its own row only. | `verify_musicundo.py` |
| Play with my drawing and Hear the loop sit under the timeline, whichever door is open. A tapped tempo belongs to its song (kept in the drafts, gone with a new song), and every count of beats is of what is heard, smooth restart included: an end that settles on 8 beats means 8 out of the speaker. Only an end let go on the strip settles on whole bars; typed, stepped and locked ends never do. Zoomed in, an end let go near whole bars stays and the tempo becomes the one that makes them exact, of what is heard too. | `verify_musicbeat.py`, `verify_musicsnap.py`, `verify_musictempo.py` |
| The timeline's taller box glides, one tap twice as tall and one back: whole pixels, each frame painted at its own height (the stage's ResizeObserver paints, it does not ask for a frame), Hear the loop kept where it is on the screen and the timeline's top never under the header, and the drawer's growth follow told it is the person's own. Zoomed in deep the wave is drawn against the loudest in view, further out against the song's. Two fingers zoom sideways and make it taller up and down; Ctrl and the wheel zoom on a desk. | `verify_musictall.py` |
| The CLICK ticks on each beat of what plays, on the loop's own audio clock, to the millisecond, the bar's tick higher, straight to the speakers and never into a post or a file. Each beat is set half a second ahead, so a page held for less than that drops no tick, and everything set ahead is called off when the click goes off, Hear stops or an end moves. | `verify_musicclick.py` |
| The timeline's drawing lane shows the drawing: the Pad's strokes each in the ink they were drawn in, an ink that would not read 3:1 against the lane kept to its hue and made darker (or lighter) only as far as that takes it, an eraser's the accent; Flip's pages each their own picture (the strip's thumbnail, or past its cache the strip's own tile, so the lane never paints a page), their own shape kept, at the lane's height one centred on the page and the rest either side, or a shorter page the whole picture smaller, each framed in the lane's purple, the number on a small badge on a picture at the lane's height. Flip's lane grows from 34px to 52 with the box, in the frame the box does, the song and the ends' handles 8px under it; the Pad's stays 26. | `verify_musiclane.py` |
| A song in three is heard in three and counted in its own bars: Skribl hears a waltz's bar (its kicks and chord changes gathering every third beat, not every fourth), a song in four stays in four, and Beats in a bar (4 or 3, "heard by Skribl" or "set by you") sets it by hand without moving the loop. Every count of bars follows it: Beats (3 · 6 · 12 · 24), Skribl's pick, Snap and the end setting the tempo, a bar in Each press, the bigger dot, the click's higher tick and Flip's Beat rounds (1 or 2 bars in three). The tempo keeps `bar: 3` and `barBy: 'you'` in the drafts; a song in four saves what it always did. | `verify_musicthree.py` |
| ONE MediaRecorder video exporter for both editors (`lib/videorecord.js` recordVideo(): each editor gives frames, a painter and the loop). It carries the music when music is on -- including on the route that reaches it BECAUSE of the music (the MP4 declines without AAC) -- one frame per beat with the first not doubled, and is a success only if something came out: an empty, errored or unreadable recording, or one with no frame in it (a header alone), downloads nothing and says so. It names an audio codec in the type it asks for only when there is an audio track: Gecko's recorder waits for one and never stops. It pushes each frame in Gecko too, whose requestFrame is the stream's, and it waits for the recorder's stop with a limit, Cancel working throughout. | `verify_videoexport.py` (the file's own tracks and frames, read from the download; the no-AAC route driven through the Video button on both editors; a stand-in recorder that hands back a header with no frame, on both editors; one that waits as Gecko's does, on both editors with no music; requestFrame moved to the stream, on Flip; a recorder that never answers its stop, and Cancel while it is waited for, on both editors) |
| An account draft is overwritten only from the copy the save was made from (`baseUpdatedAt`, compared as an instant); a save from an older copy is a 409, and the editor keeps both by saving it as a copy. A save without the field (an older client, a host's own code) overwrites as before. Two saves made together never both pass and never answer 500: on PostgreSQL the row lock makes the second a conflict, and on SQLite, whose lock is the whole file's, a save that meets another write is a 409 with busy:true, never called a conflict. | `verify_clouddrafts.py` (section 9, two signed-in devices), `verify_draftrace.py` (twenty pairs at once, and a write to another draft, on SQLite and on PostgreSQL) |
| How long a page lasts and how much of a drawing page is revealed are `lib/holdtiming.js`'s answers, not each surface's. Four surfaces render a reveal and they agreed in the middle of the range and disagreed at both ends. | `verify_sharedrules.py`, `verify_inline.py` |
| A drawing page is EXEMPT FROM fps everywhere, the exported file included — a file has frames, so it samples the page's millisecond timeline rather than re-denominating the page in slots. | `verify_sharedrules.py` |
| Every Draw-on page begins empty, reveals monotonically, reaches its COMPLETE recorded state, and only then yields to the next page. This is about the COMPOSITION of the clock's page, its progress and dueCount — all three were individually correct while the terminal state could never occur; lib/holdtiming.js displayAt() is that composition — so it is asserted through the actual surface clock, on both players. | `verify_sharedrules.py`, `verify_inline.py`, `verify_hold.py` |
| A media reservation that was ATTEMPTED and failed raises; 0 is returned only for the designed no-ops. The caller checks the COUNT, so a post is refused on a short claim whatever the helper's failure mode. A swallow here publishes a post against media a sweep may already have deleted. | `verify_sweepjob.py` (the real helper, a real failing write), `verify_createpost.py` (the post refused, driven through a BEFORE INSERT trigger rather than a mock) |
| The orphan sweep NEVER deletes on an unanswered claim query — at the batch read and again at the per-key re-check before the delete. "There are no claims" and "I could not find out" are different answers, and only the first permits deletion. | `verify_sweepjob.py` (`skipped_unverified`, so an operator cannot read it as a clean run) |
| `pending_media_ready(engine)` answers PER ENGINE. One process-global bool let whichever database asked first answer for every other one, in both directions. | `verify_sweepjob.py` (two engines, two schemas, one process, both orders) |
| A counter that two requests can touch is incremented BY THE DATABASE. `views_total` was read-modify-write, so two viewers interleaving lost one play -- silently, permanently, and worst on the posts Hot ranks. | `verify_hot.py` (asserted on the SQL the route emits: a bound parameter is a snapshot, a named column is not) |
| The effective request cap is the LOWER of MAX_CONTENT_LENGTH and SKRIBL_MAX_REQUEST_BYTES -- but the env value participates only when it is actually set, or Skribl's own default becomes a silent ceiling on every host that raised theirs. | `verify_txcontract.py` (both directions; the refusal asserted as 413 exactly, so no validator's 400 can stand in for it) |
| A gzipped body is ONE member. Trailing or concatenated data is refused, never ignored -- `eof` only says the first member ended. | `verify_txcontract.py` |
| An author's own listing shows everything they own, unlisted included; every other reader still sees only public. Unlisted means hidden from PUBLIC listings, not hidden from its author. | `verify_privacy.py` (owner, another signed-in user, and anonymous all driven) |
| Copy describes the ownership model IN FORCE. The browser-held sentences are false under host accounts, and a shared help include is two instances until it has been driven on both editors in both modes. | `verify_hostseams.py` |
| A background photo lands where `lib/photofit.js` says, on EVERY surface -- editor, `/s/<id>`, and the in-post player a feed and the profile stage use. The in-post player hard-coded cover and cropped what the author had fitted. | `verify_inline.py` (solid photo, 4:1 on 4:3, sampled at three rows; both fits driven) |
| A background photo's OPACITY and BLUR travel with it too. The editor and `/s/<id>` apply both as CSS on a real `<img>`; a feed box has only a canvas and applied neither, so a photo composed at 40% painted opaque and one composed soft painted sharp, on every host embed. | `verify_inline.py` (two properties, two rows: a 40% photo measured against its composite over the ground, and a hard edge whose step collapses under blur -- each calibrated by removing only its own line) |
| Both playback surfaces carry a full screen control; whatever goes full screen contains its own way out -- only that subtree renders, so the transport row is not on screen -- and the DRAWING grows to the screen rather than the wrapper alone. A page that has no exit control inside the canvas is not offered the control at all, which is the editor running the `#skribl=` fallback player. | `verify_player_isolation.py` (driven: entered, exit asserted VISIBLE, left through it; the canvas measured in the page and in full screen; the editor page driven through the fallback's own localStorage key) |
| A post is the same height resting, playing and paused, and its line says its numbers and shows its shape BEFORE any payload is fetched, from the listing's `line` -- whose numbers are ports of the player's own functions, so the line at rest and the drawing playing cannot disagree. | `verify_inline.py` (THE POST) |
| Every template that loads `inlineplayer.js` also loads `lib/photofit.js`. The profile page hand-copies the in-post player's asset list, so it missed the module and fell back to a centred cover on a photo its author had fitted. | `verify_library.py` (matched on the `skribl_asset()` call, never on the comment beside it) |
| Every mandatory external lane writes an attestation NAMING THE TREE it describes. A lane that is merely claimed by a CI job is pending, not covered — existence of a job is not a result. | `verify_docs.py` (mechanism calibrated against a wrong-tree attestation) |
| Both editors build the pen palette from `lib/palette.js` — same list, same order, from the lib and not from a copy. | `verify_parity.py` |
| Every grey the chrome paints is a token, not a literal — including the `rgb()` function form, which the first version of the ratchet could not see. | `verify_surfaces.py` |
| `color`, `fill` and `stroke` hold no colour literal except `#fff` and `#0d0f14`. A red is not a neutral, so a grey audit walks straight past it. | `verify_theme.py` |
| A drawing's ground never follows the theme. Only a NEW drawing starts on the theme's ground, Paper in light and the dark canvas in dark, and a blank one follows a switch until a stroke, a hand pick or a restored draft makes it the person's. | `verify_theme.py` (painted, held, lit and saved, on both editors) |
| The canvas's edge is one screen pixel (an inset ring scaled by `--hair`, never a border, which Chromium will not draw under 1px), one line at every side, the Pad's and Flip's alike: the Pad's ring, the ground's ink at 18% on a dark ground and 22% black on a light one, with no second line along the top; Flip's frame lays the same ring over its own edge (its 2px band is transparent and the ground fills it, padBox() still reading it), and none in full screen. | `verify_visual.py` (THE CANVAS'S EDGE) |
| The site's lines are one screen pixel: every outline a ring of `--edge` outside a transparent border, so nothing moves; a card's in `--card-edge` (its line laid over the card and made solid, so a dark card keeps its hairline), a separator a line of `--edge` above or below its row; the Gallery's tiles sit on the light page with the cards' lift; a field's edge reads 3:1 on its white. A state that colours an edge (invalid, a hover, Following) shows as it did, its ring stepping aside. | `verify_socialposts.py` (17) |
| A drawing on the site draws its edge in one screen pixel (the edges, part four, its last; `social.css`): in a post, on Home's card and its own page, a comment's, the composer's draft and Blooby's card, the in-post player's own border is made transparent through the token the site already sets (`--border`), so nothing moves, and the box wears a line of `--edge` outside it in `--draw-edge` (the drawing's line as it looked over the box's own ground, made solid) and, on the light page, the cards' own lift (`--draw-lift`, `--card-drop`; none in dark). Skribl's player is not restyled: the site draws it. | `verify_socialposts.py` (17: off the paint at 3x, the border transparent, the line one screen pixel by its own measure; the lift against the same box with its shadow cut) |
| The editors' sheets and drawers draw their lines in one screen pixel: a card or control keeps its border's width, transparent, so nothing moves, and wears a ring of `--edge` outside it, in `--menu-card-edge` (its line laid over its white) or, for a drawer's paper, `--menu-paper-edge`; the glass's rim is the same line; a state that colours a border shows as it did, its ring stepping aside; a row's own tint reaches the line, and a picture card's inside pixel is its picture's (a phone recording's card wears its frame's tint; a drawing's card, in Ask's answers and the little book, the drawing's own ground, which `lib/learncard.js` hands it). | `verify_contrast.py` (THE SHEETS' EDGES, ONE CARD), `verify_book.py` (8: the drawing card's inside pixel at 3x) |
| The Library's and Skribl's Gallery's lines are one screen pixel (pagemenu.css's --hair and --edge, on both pages): every outline keeps its border's width, transparent, so nothing moves, and wears a ring of --edge outside it, in its line laid over what it was drawn on (a card's --card-edge, the site's and the editors'); the tiles and the rows keep their lift on the light page; a search field's edge is the site's --field-line, 3:1 on its white; the page menu's card in --menu-card-edge and its rows the Pad's thin line, from where the words start; the recovery-key panel (posted.css, on the Pad, Flip and the Library) in rings of its own colours. A state that colours an edge shows as it did, its ring stepping aside. | `verify_galib.py` (10) |
| A drawing's link page draws its lines in one screen pixel (the edges, part four; styles.css, reaching it in player.css): `--hair` and `--edge` on every page's body; the round buttons, the More card, its point (drawn 1/`--hair` as large and scaled back) and the line between its rows, the speed chips' card, the scrubber's bubble, the way back to a host's site and, on a desk, the column's sides: each border kept, transparent, so nothing moves, and a line of `--edge` outside it in its line as it looked over its own ground, made solid. The solid lines are written once from `--hl` and `--hls`, the hairlines' strengths, which each theme sets and Increase Contrast swaps for the -hc ones as it swaps the hairlines. The speed chips, the bubble and the column are the editors' too, and the band's in `fullband.css`. Kept bold on purpose: the scrubber's head's ring; toned by the drawing: full screen's glass buttons and, since No dinge, the last four, its x. | `verify_linkpage.py` (THE LINK PAGE'S EDGES: off the paint at 3x and a desk's 2x, the border transparent, the line one screen pixel by its own measure; Increase Contrast), `verify_player_isolation.py` and `verify_jsstrip.py` (the link page's CSS budget) |
| A token named for the CANVAS is not chrome and is exempt — naming it in `:root` is what makes that a decision rather than a literal somebody missed. | `verify_surfaces.py` |
| A run whose suite names begin with `_` is a scratch probe and must never be published as the project's result. | `stamp_docs.py` refuses it |
| Hiding a control is only safe when nothing reachable ONLY through it becomes unreachable. | **no enforcer** — found by looking; `beginPinch` revealing the zoom HUD is what made hiding Magnify safe |
| A colour ratchet cannot see a mark that is white ON PURPOSE — five vanished in light mode and were found by eye. | **no enforcer** — `#fff` is exempt because it is nearly always text on a coloured fill |
| An anonymous retry replays to the post the first request made, scoped by a client capability, and the key that deletes it was minted before the answer could be lost. | `verify_apiedges.py`, `verify_posted.py` |
| The Pad's idempotency key is judged on the drawing, not on serialise-time stamps; a Pad entry in Your Skribls holds its revocation key. | `verify_posted.py` |
| The Pad, Flip, the player, the library and the gallery carry the app's identity (manifest, theme-color, icons); the feed, a host's page, carries none. | `verify_identity.py` |
| From the Home Screen (the Blooby app's or Skribl's own), the top 6px of the Pad, Flip, the Library, Skribl's Gallery and a drawing's link page are their own ground (`.app-edge`: styles.css for the editors, reaching the link page in player.css; pagemenu.css for the Library and the Gallery), fixed, over the header and under every sheet, so iOS 26 lays no glass blur over the top of the page: the page is marked `data-skribl-app` before the first paint (`_skribl_app_boot.html`), on the editors the same answer `lib/homescreen.js` gives; a tab never has it, the header's controls start below it, and the link page's full screen (an iPhone's stand-in too) covers it. | `verify_identity.py` (THE APP'S TOP EDGE) |
| A page that asks for the cross-fade between pages (`@view-transition`: the Pad, Flip, a drawing's page, the site's pages) has the stylesheet that asks loaded when `<body>` starts, where Chrome decides whether an arriving page fades: Skribl's theme boot, an inline script, comes after it, so a first visit (nothing cached) fades too. | `verify_menu.py` (the Pad, Flip, a drawing's page), `verify_socialsettings.py` part 4 (Home, Explore) |
| The feed says it is a developer demo; its consumer states carry no code, and its error state can retry. | `verify_inline.py` |
| Every live bar and header control answers a tap 44px tall (40 at the 320 safety net); the visible pill is a different floor. | `verify_layout.py`, `verify_a11y.py` |
| Where one line of an icon ends on another it ends ON it: no round end pokes out of the line it meets by 0.06 units or more (the owner's "little nub" on Make's pencil, Nov 27), in any icon in the tree: the site's, through their macros, and every inline svg of the templates and scripts. An overhang drawn on purpose (a bin's lid, a bell's stem) and a gap are not nubs. | `verify_icons.py` (THE ENDS; `harness/tools/iconends.py` is the instrument) |
| BLOOBY'S ICON SET (the owner's "Default to yes on all", Nov 27; the rule is written at the top of `social/_icons.html`): every site icon in ONE LINE, 2.1 (but Blooby's own 1.6, Search lit, a draft's tiny chip, the quote's 1.7 and Make's pencil, the owner's "Leave it alone"); each icon's ink CENTRED in its box within a third of a unit (but Play's triangle, your face's curl, Blooby and Make's pencil); every icon a sheet's rows draw, read off the templates, ONE HEIGHT, 18.33 units at its longer side with its line (16.8px at a sheet's 22px), `plus` and `back` drawing a sheet-height copy (`fit`) so Follow's plus and the way back keep theirs; the gear's hole at its teeth's middle; the ☰, the envelope and the bell at the top of a phone's Home at one size and one line. | `verify_icons.py` (THE BLOOBY SET), `verify_socialletters.py` (15) |
| The Motion Smear's trail reaches back to where the object came from, measured on the render. | `verify_tween.py` |
| A closed shape is counted and named when it is smeared; an open arc is not. | `verify_tween.py` |
| A live smudge frame is as bright as the settled one, and the cheap path takes no layer round trip. | `verify_smudgeblur.py` |
| A client capability is minted from Web Crypto or not at all: without it neither editor sends a client header and the server mints the key. | `verify_posted.py` |
| The seal holds before its final render until every external lane attests the frozen tree, or its hold expires and the record says which lane is pending. | `verify_docs.py` |
| Somebody reads main: a push to main whose battery FAILS opens an issue titled "main is red" (or comments on the one already open), and the next fully green push closes it. A cancelled run does neither. | `verify_docs.py` (`harness/tools/mainwatch.py`'s decide() driven case by case, and the `main-watch` job's needs, condition and permissions read as structure) |
| The public gallery is opt-in: a post carries `visibility: "public"` only when its author ticked "Show in the public gallery" on the Pad or Flip sheet, the key is omitted otherwise, and `/gallery` shows exactly the posts that carried it. Compose mode renders no such box unless the host asks the author (`?gallery=1`): then "Show in the Skribls gallery", off, a gallery caption that glides open under it once ticked, and the payload handed back carries `"public"` and the caption only with the tick, on the Pad and Flip; the reference host keeps what it says. "Viewers start at" shows in compose mode too. A card's row keeps time only while the card is near the screen. | `verify_gallery.py`, `verify_example.py` (the reference host's two posts) |
| A report is a row in an operator's queue, never an action: `POST /api/skribls/<id>/report` writes one row per (post, reporter), a duplicate writes nothing, an unreadable post 404s, the post's visibility is untouched, and `takedown --reports` lists it. | `verify_tilereport.py`, `verify_takedown.py` |
| `/library` is the profile's tab and a profile is somebody's: with no host identity it shows what this browser posted (unlisted included, from the same list "Your Skribls" keeps), with one it reads the listing's author filter, and in neither case the public listing. Its stage goes full screen and comes back. | `verify_library.py` |
| A play is counted once per client per post per UTC day, from the payload fetch every player makes; Hot is the last seven days of those, computed from the rows; search is the listing's own `q`; the gallery ranks and filters nothing itself; no address is stored. | `verify_hot.py` |
| A view row does not outlive the window it serves: `skribl_views` is purged past `VIEW_RETENTION_DAYS`, never inside `HOT_DAYS` whatever a host configures, and `views_total` is untouched so the lifetime count is not a function of when the janitor last ran. | `verify_hot.py` |
| The gallery renders the answer to the request the bar is showing. A tab or a search made while a listing is in flight is never dropped, and a superseded response never commits. | `verify_hot.py` (the tab and the search driven during a held request) |
| A control that reports success reports the truth: Copy link says copied only when the text reached the clipboard, on both the row and the stage. | `verify_posted.py`, `verify_library.py` |
| User text printed into an operator's terminal carries no control characters, in the queue and in the one-post view alike. | `verify_takedown.py` |
| A posted Skribl carries no photo location, camera tags, song tags or file names: `create_post` strips them before anything is stored (skribl/mediameta.py) and `GET /api/skribls/<id>` strips a post stored before that on the way out, without writing it back. Pixels, samples and a photo's orientation are untouched. | `verify_mediameta.py` |
| What a stroke point carries beyond x, y, size, a short colour, a time and its two flags counts against the extra-content cap, like every other key nothing else bounds. | `verify_mediameta.py` |
| An operator's takedown stays down: `withheld` is set and lifted only by `python -m skribl.takedown`; no post is created withheld, no author can choose it, and an author's key cannot change it (it can still delete). | `verify_mediameta.py`, `verify_takedown.py` |
| A drawing keeps ITS OWN aspect inside the in-post player's 16:9 box. The canvas's CSS width and height stay `auto`: both definite has each axis clamped by its own maximum, independently, which stretched every non-16:9 drawing on the feed, the profile's stage and every host's embed. | `verify_inline.py` (three shapes, two widths), `verify_library.py` (the stage) |
| The in-post compositor's offscreen layers use the scale `ctx.setTransform` was set to, never one derived from the canvas's CSS size. | `verify_inline.py` (the same drawing rendered with the compositor disabled at source) |
| "Your Skribls" is the profile page, not a drawer: both editors' menu row links to `/library`, the list renders there through the same module with the same custody rules, and a row's gallery switch changes the post's visibility on the server and in the record. | `verify_posted.py`, `verify_library.py`, `verify_a11y.py` |
| The demo signs in only a browser that posted `SKRIBL_DEMO_LOGIN_KEY` (16+ characters) from the `/demo-login` page (a key in the address signs nobody in, and only the posted Sign out button signs out); unkeyed it is anonymous, never everyone. The cookie holds a mark of the key, so rotating the key signs every browser out, and guesses spend the attempts budget. | `verify_hostseams.py` |
| A CSRF token is signed and bound to the signed-in user through `init_skribl`'s own wiring; a forged write is refused before it is charged to anybody's rate budget. | `verify_csrf.py`, `verify_hostseams.py` |
| The site at `/social` is the demo's own app beside Skribl, through Skribl's public seams only; `SKRIBL_SOCIAL=0` leaves it out, and a site that cannot start is logged and left out, the demo's pages answering either way. The top of an address `SKRIBL_SOCIAL_HOME_HOSTS` names opens the site's Home, while every other address, the demo's own name among them, keeps the Pad at its top. | `verify_social.py` |
| At an address `SKRIBL_SOCIAL_HOME_HOSTS` names, the Pad and Flip wear the site's `blooby.` (`app.py` `_site_brand`): painted, the word in Skribl's purple and the period in Blooby's blush, the line where skribl's was and nothing else in the header or the dock moved, named Blooby; and their first open writes blooby, its blush dot falling, splatting a little and becoming the period (landing B, `social/static/brand/blooby-hello.json`, drawn through the real Flip editor by `harness/tools/make_hello.py --site` from the site's own mark and tokens), gliding on every frame, once by its own key, still and fading under Reduce Motion. At every other address the demo is byte for byte as it was: skribl, and its hello with the bounce and the wink. | `verify_hello.py` (its site part; `HELLO_PART=site` runs it alone) |
| The site at `/social` lets people in by invite only, with passkeys (discoverable, user verification required, the sign count stored and checked, made and used only at the site's own addresses once `SKRIBL_SOCIAL_HOSTS` names them, else the request's own); a link's code is after its `#`, so no log holds it, and only its hash is stored; every state-changing request to the site carries its token and its own Origin; sign-ins, joins, link checks and an invite's tries are limited in the database, a try written before it is counted so no more than the limit are let through even at the same instant; "Sign out everywhere" ends every cookie made before; deleting an account deletes the person, their passkeys and their invites; Invites is a 404 like a missing page to anyone but an admin. While somebody is signed in to the site, the Pad posts as them. | `verify_socialauth.py` |
| The site's tables are `social_...` on a migration chain of their own (`social/alembic.ini`, stamped in `social_alembic_version`), run once per start by `gunicorn.conf.py`; Skribl's chain and tables are never touched by it, and a chain that fails is logged while the demo serves on. | `verify_socialauth.py` |
| A person's profile at `/social/@<handle>` (any case; a kind 404 for nobody) shows their name, handle, their counts (Follows, below), bio and their tabs (the next row), the same to them as to anyone but for what is theirs alone; an empty tab tells its own person what puts something there, and anybody else only that there is nothing yet. Their face is a skribl they drew in the Pad's face mode (`compose=1&face=1`: square, no Flip), kept UNLISTED through `create_post` in the transaction that names it, replaced and deleted through `delete_post`; a face never carries a photo: in face mode a photo (Trace a photo) is a guide to trace, left out of the face and its card by the Pad and dropped by the site if sent anyway; whatever the Pad hands back goes to Your face's circle first, starting with all of the drawing inside it, and Edit this face reopens the face in the Pad; it draws itself once on the profile at about 4x (finished at once under Reduce Motion) and is a still picture everywhere else, with no fetch; before one is drawn, an empty circle, never a stock silhouette. | `verify_socialprofile.py` |
| A profile's tabs at `/social` (`profiles.py`, `_profile.html`, `tabs.js`; the map's step 4) take the place of its Skribls heading and Skribl's Gallery section: Posts · Gallery · Likes · Bookmarks · Drafts on your own page (Bookmarks since the owner's "All yes", Nov 14), Posts · Gallery on anybody else's, Posts first; a strip of 48px tabs, the screen's width on a phone and the column's on a desk, your own five SIZED TO THEIR WORDS on a touch phone (16px or more between the painted words at 402 in every face here, DejaVu Sans included; short of room the edges give first, then the tabs, never past the screen, held at 360px too) and equal columns on a desk, the chosen one in the first ink with the bar's own pen line under it (painted; the chosen tab's own, drawn inside it, so it is there before any script runs), the others in the second. Each tab is a link with its own address (`/gallery`, `/likes`, `/bookmarks`, `/drafts`): a tap draws the line under the tab, the one it left fading where it was, fades the panel and changes it only unseen, the page holding still (under Reduce Motion the line put there whole, the panel still fading), then the address is the tab's, so the back button, forward, a reload and a shared link land on it. Posts: their posts as Home's one card, newest first, Load more. Gallery: every drawing and Flip they shared as the Gallery's tile, a post's opening its post and one shown outside a post its own page (`/social/b/<id>`), never a face or a comment's drawing; and on your own page alone, THE EYE (the owner's "Yes, the eye in view", Nov 14): each tile an eye at its top right on the ▶'s glass (painted, 44px, 13px in), one tap hiding the drawing from the Gallery (crossed, "Hidden", faded to 55%, the site's toast "Hidden from the Gallery" with Undo, never over an eye), a post's by the site's own flag (`social_posts.gallery_hidden_at`; the post stays on Home and in your Posts), one outside a post by its visibility in Skribl (public or link-only, `set_post_visibility` as its author), your link-only ones there too, hidden; nothing of it on anybody else's page or in its source, every tap counting when pressed fast. Likes, Bookmarks and Drafts are yours alone, nothing of them on anybody else's page or in its source, their addresses sending anybody else to the person's page: Likes the posts you liked, newest liked first (posts only, nobody a block hides, nothing taken down, a mute changing nothing; on its own index); Bookmarks what you kept (its own row, after Likes'); Drafts the drafts Skribl keeps on your account (`list_drafts`), newest saved first, as tiles; A TAP ON ONE OPENS IT INSIDE A POST (the owner's "All yes", Nov 19: `compose.js`, `SocialComposer.draft`): the composer's sheet with the editor that made it over it, the sheet not painted until Add brings the draft back attached (only the editor is seen rising), put away without Add the sheet going with it and you on your drafts as you were; the tile is still a link to the editor's own `?draft=<id>`, which a new tab opens as the editors' own Your drafts does. Delete post on a card of your own page keeps you there (never Home and its note): the post folds away where it was, a fade and then its room closing, the next card rising over many frames (under Reduce Motion the fade, and the room gone at once once unseen), the site's toast saying so in Home's words near the finger (no Undo, never over the next card's ⋯), the last one gone leaving the tab's own. Every word at 4.5:1, every control 44px. | `verify_socialprofile.py` (1, 15, 16, 17, 18, 19, 20), `verify_seam.py` and `verify_hostseams.py` (A PERSON'S DRAFTS), `verify_socialauth.py` (the likes index, the eye's column), `verify_sociallikes.py` (11), `verify_socialbookmarks.py` (6) |
| A post at `/social` is a drawing and words (up to 500 characters), made in the composer (the next row): Draw and Flip open Skribl's own editor over it in compose mode, asking for no gallery tick since Nov 19 (the sheet still asks "Viewers start at"), and Post sends the skribl through `create_post` and the site's `social_posts` row in one transaction, unlisted (a payload that says public is still kept so); with nothing drawn, Post says so and sends nothing. The feed is everyone's, newest first, each card still until tapped, its time a link to its own page a tap lands on (44px; the face, name and @handle still the person's, nothing on the card moved) and its words opening it too (a link of their own until mentions, Nov 15; now the card's ground, an @handle in them that is somebody the link to that person), a tap anywhere else on it opening its page too but for what has a job of its own (the drawing plays and never opens the post, ⋯ and Share their sheets; a drag, or a click that ends a selection, opens nothing), its 💬 there even at none ("Comment"), its drawings described through `describe_posts`, Load more in place by a cursor that names no internal id; and it holds posts alone, Following and Everyone, signed in and out (the map's step 3): a drawing shown in the gallery outside a post is on no Home and keeps its own page (`/social/b/<id>`, with a Delete that is its author's alone), and its maker's page, and a cursor from before that names one reads as its time. A post's own page plays its drawing by itself, sound off, never under Reduce Motion; under its date is THE ANSWER BAR, the one place to answer (the Calm Post Page, the owner's "All yes to everything", Nov 20: "Say something…" and Draw back, fixed on the bottom bar on a phone, in the column on a desk where the box opens in the line's own place; `_comments.html` `answer_bar`), then small quiet labels over what is there ("3 draw-backs", "7 comments") and nothing over nothing; it has NO More from (its author's other drawings are not on it, nor in its source: until Nov 20 they were, read one person at a time through `list_public_posts`) and no Make your own (the bar's and the rail's Make open the composer there). ⋯ is Bookmark (the Bookmarks row), Copy link, Share…, Report (into the site's own queue, piece 5) and signed in Block, or on your own post Delete (one card, the risky rows a card of their own, no Cancel: the row after the ☰'s), asked once, taking the words and the drawing (from your own page the post then folds away there; anywhere else Home says it went); posting and deleting need the page's token and its Origin, and posting is limited per person; deleting an account takes its posts. | `verify_socialposts.py` (section 3 the post's page, section 9 Home's posts only, sections 10 and 11 the card's ways in) |
| THE COMPOSER at `/social` (`compose.py`, `_compose.html`, `compose.js`; the owner's "Yes", Nov 14, to the mock beside Bluesky's new-post screen, B; part two of the map, its item 1): ONE MAKE, EVERYWHERE. Signed in, every page with the bar carries it and no two-door sheet, and Make (the bar on a touch phone, the rail on a desk) opens it (Home has no box of its own since the owner's "All yes", Nov 14: Make is the way to post); signed out Make keeps its two doors into Skribl's own Pad and Flip, and the page holds no composer. Make's own sheet made tall: on a phone almost to the top (5vh short of it), its tools riding above the keyboard while ITS PAPER RUNS DOWN BEHIND IT to the screen's foot (a spacer the keyboard's height, `.cmp-sheet::after`; the small comment sheet the same; Nov 20, so no strip of the page shows under a sheet: `docs/SOCIAL-SITE.md` section 26), on a desk a 600px card in the middle, one height whatever it holds; it glides up and down (read on every frame), and under Reduce Motion fades where it sits. Cancel top left, Post top right, waiting (`aria-disabled`, an inactive control: the second button's lilac in the chosen violet, at full strength, No dinge; it faded to 0.45 before) until there are words or a drawing (words alone are a post: the owner's "I like your pick", Nov 16; no drawing box on its card, never in the Gallery; the database's rule `ck_social_posts_drawn_quoted_or_said`), a press with neither saying what is missing and sending nothing; your face beside "Say something…" (18px); the drawing under the words PLAYING in Skribl's in-post player (never under Reduce Motion), with Edit drawing and Remove; Draw, Flip and Yours along the bottom and the characters left at their end (500). A post holds one drawing: with one attached, a tool says so. YOURS, "Use one you made": the one pill Drafts | Drawings (the words fade out before it fades in, the sheet's box the same on every frame); your drafts (`list_drafts`), a tap opening the editor that made it over the sheet with the draft on its canvas (`lib/composehost.js` `openDraft`), Add to post attaching it; your drawings shared outside a post, link-only too, never a post's, a face or a comment's drawing, a page at a time; a tap attaching it as it is (no Edit drawing). ONE DRAWING, ONE CONVERSATION: an older drawing posted is the post's drawing (nothing new in Skribl), its hearts (their moments), comments and answers moving onto the post with their times in the same transaction (a move refused leaves no post), its own page sending people to the post, its old like and comment addresses taking nothing new, the Gallery showing it once with the one conversation's counts, Activity naming the post with nothing new and the dot dark; one hidden from the Gallery stays hidden; one in a post is never posted again (409), and somebody else's, a face or a comment's drawing is as gone as one never made. Every word on it at 4.5:1 on what is painted behind it, every control 44px, its field 18px. | `verify_composer.py`, `verify_socialposts.py` (1 to 3 from Home's row; 19, words alone), `verify_socialauth.py` (14, the rule's migration) |
| Explore at `/social/explore` is the Gallery of everyone (`social/gallery.py`, `explore.html`, `_gallery.html`, `explore.js`; the map's step 3): every drawing and Flip the site's people shared, in a post or not (the owner's "Yes, your picks", Nov 14: a post's tile opening its post, a drawing shown outside a post its own page, `/social/b/<id>`), two reads a page long in one order (the site's posts, and the rest through Skribl's `shared_skribls()`, never a query of Skribl's tables) merged by one cursor, never one kept link-only, a face, a comment's drawing, one its maker hid from the Gallery or one by somebody not on the site; the bar calls it Gallery (its address and Blooby's icon kept). Signed in, Following | Everyone, Home's own pill (the people you follow and you, or everybody; opening on Everyone), and New | Hot beside it on one line, the search box under them on a line of its own, whole (since Nov 19: sharing New | Hot's line it had 178px on a 402px phone for words that need 217) (Hot is plays in the last seven days through Skribl's `recent_plays()`, most first, both kinds in one order; the search a post's words, a drawing's title and its maker's name and @handle, and people too, People first: Finding people, below); a change glides its pill and fades the tiles, changing them only unseen, the page never scrolling, the address saying what is shown. Two tiles across on a phone and three on a desk, each ONE link to its post (a tap anywhere on it, a click, the keyboard): the drawing whole in 650 x 486, cut out of its share card (`_gallery.html` `plate_frame`, a draw-back's tile's rule too), the box around it the drawing's own ground (`plate_ground`, from Skribl's `describe_posts` `ground`, a hex colour or nothing, from a column written at post time, no payload crossing; the paper where it is not known), a drawing made on a picture with that picture at its sides (`plate_fill`, the row after this one), its "▶ 15 sec" what the player's play button says at rest without "drawn in" (a Flip its pages), the maker's face (the empty circle, never an initial) and name as written, cut with … only when it doesn't fit, the hearts and comments only when there are some. The first visit (Home signed out, `gallery.first_visit`) keeps its welcome and under "Fresh from everyone" holds the six newest of these tiles, as the Gallery shows them signed out (every skribl), then "See the whole Gallery ›" to it, where Skribl's own Gallery section was; with nothing shared, the Gallery's own words. Nobody a block hides or you muted, and nothing taken down (its maker's view too), in the query; Load more by a cursor naming no internal id, Hot's holding the moment it ranked at. | `verify_socialposts.py` (9, 13, 14), `verify_socialmute.py` (6), `verify_socialsafety.py` (4, 11, 12), `verify_social.py` (2, 4, 5, 9), `verify_createpost.py` (11, the ground), `verify_seam.py` and `verify_hostseams.py` (WHAT IS PLAYED MOST, WHAT PEOPLE SHARED) |
| A drawing made on a picture (a photo, or the picture the Pad began on) keeps that picture at its sides on every tile that frames a plate (the Gallery, a profile's Gallery tab, the first visit's six; the owner's "Yes to both, build them", Nov 14): a second copy of its plate behind it (`_gallery.html` `plate_fill`, social.css: covering the box a quarter over, blurred 16px, saturate 1.1, 0.9), FIRST in the box and nothing with a z-index, so the plate paints over it and the ▶, and on your own Gallery tab the eye, over both; a plain drawing keeps its strips in its own ground; hidden with the eye, the picture fades with the drawing. Skribl says which from two columns written at post time, `ground` ("#rrggbb", or "" for none) and `on_photo`, by the player's own rules (`validation._payload_ground`, `_payload_on_photo`; `create_post`, both editors), on a columns-only revision; `describe_posts` reads the drawing only where a column is NULL (a CASE), until `python -m skribl.backfill_ground` (`skribl/backfill_ground.py`: a dry run by default, small batches, resumable) fills it in. | `verify_socialposts.py` (15), `verify_createpost.py` (11, 13), `verify_hostseams.py` and `verify_seam.py` (WHAT A DRAWING IS PAINTED ON), `verify_migrations.py` (the revision and the command), `verify_postgres.py` (both on PostgreSQL), `verify_sweepjob.py` (its `--app`) |
| On `/social` anybody can report somebody (a person's own reasons) or a post or a drawing (the Gallery's reasons and a child's safety) into the site's own queue, once per reporter, with nothing taken down by it; signed in, anybody can block somebody from a profile's or a post's ⋯, asked once: both ways and quietly, on the site's pages and on Skribl's own (its listings, a drawing's link page, payload and card, through the feed filter and visibility policy the host installs); to the one blocked the blocker's profile is nobody's; Settings lists who you blocked, each with Unblock, and only the blocker lifts it; deleting an account takes its blocks and leaves the reports naming it, naming nobody. Skribl's own report sheet offers a child's safety, and its queue lists those first. Your Reports is an admin's alone (anybody else meets the same 404 as a page that is not there): one card per thing, the site's reports and Skribl's together, a child's safety first and blurred until opened; Keep it closes the reports and hides nothing; Take it down hides a post, a drawing or a person from everybody else at once, deletes nothing and closes the reports, Skribl's too; its maker sees the note, and a person taken down shares nothing new. Skribl's `list_reports` and `close_reports` name nobody and take nothing down. The rules (Terms, Privacy, Community rules) are three plain-words drafts anybody can read, each saying so, each linking the others, linked from Join and Settings. | `verify_socialsafety.py` |
| A post's own page at `/social` holds its comments, and so does a drawing's shown outside a post (`/social/b/<id>`), by the rules of its page (gone to anybody a block either way with its maker, its takedown or its maker's, or its deletion in the Library hides it from, its comments with it): newest first, twenty a page with Load more; THE THREAD (step 1 of `docs/SOCIAL-SITE.md` section 18, the owner's yes, Nov 17): each comment in a bubble (the site's card, its lilac edge, its lift; a face not drawn yet its initial) with its row under it (Reply, the word on a desk only, and ⋯), a reply keeping the reply it answers (`answers_id`; empty for the replies from before it, which answer their comment), THE LIST (the owner, Nov 17: "a list of direct replies first"): a list shows the direct replies to what its page is about, each with the count by its talk cloud (every reply under it the viewer may see, at any depth; on a desk in the word Reply's place), and under it its conversation followed down, BLUESKY'S WAY WITH OUR LOOK (the owner's yes, Nov 18): its first reply, the first reply to that, ten deep, in one column, the faces joined by the lilac line straight down, then "Read N more replies" to that one's own page; OR, FOR WHOEVER PICKED IT IN SETTINGS ("Replies: As a tree", kept with the account, `Person.replies_view`; the owner's "All yes", Nov 28; `docs/SOCIAL-SITE.md` section 55), THE TREE: every reply under the one it answers, oldest first, a step in, two steps at most, then "Read N more replies", the line bending into each face (`comments._trees`); a tap on a comment (not its drawing, which plays) opens its own page (`/social/c/<id>`: the way to it, it as big as a post and marked as the one you opened, the highlight's lilac behind it at 70%, the mock's softer one (the owner's pick), and the violet ring round its face (the owner's "Yes to c", Nov 18), then its answer bar ("Reply to Eli…"), the small label "3 replies to Eli" where there are some, and its own direct replies, oldest first, each followed down the same way); a reply posted continues a conversation followed down to the one it answers, else its count takes it and glows; the box behind the answer bar's line, "Say something…" (an icon at a "Comments" heading's end until the Calm Post Page, Nov 20; a phone's sheet, a desk's fold that glides open in the line's own place, keeping what was typed when put away; over the comments a small quiet label, "7 comments", and no heading at all at none) for somebody signed in, not taken down and with no block either way with the author of the post or the drawing (an answer also with the comment's author, and on what it is on), the route refusing anybody else kindly; signed out, readable, the line raising "Say something?" whose Sign in comes back with the box open; words tidied and checked as a post's, or a drawing (Draw and Flip open Skribl's editor over the post in compose mode, no gallery tick; it waits in the box until Post, is posted unlisted through `create_post` with the comment, plays only when tapped, and goes with its comment, post or account through `delete_post`); Reply opens the box for the comment without moving it on the screen; nothing by anybody a block or a takedown hides is shown or counted, nor anything under it at any depth (a recursive count), there or on Home's card; ⋯ is "This comment": Copy link and Share… (its own page), Delete comment (yours), Remove from my post (on your post or drawing) and Report this comment (the site's queue, kind `comment`; Your Reports takes one down, its author alone seeing the note); deleting a comment or a reply takes it, its drawing and its mentions, and one with replies under it keeps its place, nobody's ("This comment was deleted", or "removed" by the post's author), so they stay, a place with nothing left under it going too (`comments.retire`); a post or a drawing (through the site) takes its comments, an account its comments (places, the same way) and every comment on what it owned (`owner_id` on the row), in code, not by the cascade; a comment is on a post or a drawing, exactly one (a CHECK). | `verify_socialcomments.py` |
| Activity at `/social/activity` (`social/activity.py`, `activity.html`) is worked out from the comments, never kept: a row is a comment or a reply not yours, replying to you (`to_person_id`, whom a reply answers) or on what you own; several since you last looked on one post, or answering you in one conversation, are one row, the newest face in front, a drawing its own row, Earlier a row each; nothing by yourself, by anybody a block or a takedown hides, taken down, deleted, under a comment or a reply you are not shown at any depth (`comments.chain_shown`), or on a page you cannot see, by `comments.seen`'s rules, so every row's link (`#c-<id>`, a comment's on its post's page, a reply's on the page of what it answers: `comments.landing`) lands on its comment, which glows in the tint and fades (a drawing answer drawing itself once, the post's own waiting; nothing plays or glides under Reduce Motion), Load more bringing one on a later page; opening it marks everything seen (`activity_seen_at`). Signed in, a phone's Home and the Gallery (Explore) carry a bell drawn in our pen at the top right and a desk's rail Activity after the Gallery (the bar keeps its four), with a dot in `--new-dot` when something is new, by the same rules, asked once a request on three indexes (the comments' `owner_id, created_at` and `to_person_id, created_at`, and since mentions the mentions' `person_id, created_at`: a mention lights it as a comment does); it fades as you look. An account deleted leaves answers to it answering nobody, in code. | `verify_socialactivity.py` |
| Likes at `/social` (`social/likes.py`, `_likes.html`, `likes.js`): a heart in the row under every drawing (Home's cards, a post's page, a drawing's page: 💬, the repost (since Nov 14, in Share's place), the heart and the ⋯ (no Open › since Nov 19: a tap on a card opens it); Nov 13, until then it sat at the start of the drawing's line), 44px to a finger, `aria-pressed`, empty until this viewer likes it; how many inside it for everyone, none at zero, counted by the viewer (nobody a block either way or a takedown hides), Home's cards (posts) in one grouped read; one like a person a thing, the same tap taking it back, one request at a time; only somebody signed in, not taken down, on what is open to them (`comments.On`), with the token and Origin, 120 an hour; signed out, a sheet that signs in and comes back with nothing pressed. Each like keeps where the replay was if it was playing (`at_ms`, read through the player's `playhead()`), 0 to a day or nothing. "Liked by…" (the others only, never the maker, and no line when the maker is the only one) and its sheet (everyone, the maker too, newest first, the moment where kept) are sent to the maker alone. In Activity likes are rows, grouped since last looked and one a post under Earlier, never yourself, landing at `#liked` (the line, or with none the post's heart); they never light the bell's dot. ON A COMMENT TOO (the comment thread, step 2): the same heart in every comment's row, between Reply and ⋯ (a list's and a comment's own page), `/social/c/<id>/like`, on one the viewer may see that is not taken down and no place, kept as `comment_id` on the comment's author's (`owner_id`), no moment (likes.js reads no player for it, so no dot on the post's line), counted by the viewer; signed out "Like this comment?"; in Activity "Mira and 2 others liked your comment", its words under it, landing where it shows. A post, a drawing, a comment (a place's too) or an account goes with its likes, in code. | `verify_sociallikes.py`, `verify_inline.py` and `verify_seam.py` (the seams) |
| Bookmarks at `/social` (`social/bookmarks.py`, `_post.html`'s ⋯ and its signed-out sheet, `posts.js`; the owner's "All yes", Nov 14, to the bookmarks mock's A; part two of the map, its item 2): "Bookmark" first in the ⋯ sheet's first card, on every post and on a drawing shown outside a post, your own too, its ribbon drawn in our pen in the row's ink; once kept "Remove bookmark", the ribbon filled in --accent-ink (3:1 and more on what is painted behind it, read off the paint, light and dark); none on what is taken down or a drawing kept link-only; the row under a post unchanged. A tap keeps it or takes it away, the sheet going down, every place on the page showing it saying so at once, the site's toast saying "Bookmarked. It’s on your page, under Bookmarks." (or "Removed from your bookmarks.") beside the ribbon with Undo, never over a ⋯ (`SocialToast` `clear`); Undo says what it did with no Undo of its own and gives the ⋯ its focus back; one request at a time a post. Signed in, not taken down, on what is open to them (`comments.On`), with the token and Origin, 120 an hour; your own taken away whatever became of the thing; one a person a thing. Signed out, "Bookmark this post?", the heart's small sheet, Sign in back to the page, nothing kept. YOURS ALONE AND NOBODY TOLD: your own page's Bookmarks tab, newest kept first, Home's cards, Load more, on its own index; hidden there, never deleted, whatever a block either way hides, anybody taken down, a post taken down (your own with its note), a drawing its page no longer shows you; the muted kept; no Activity row, no dot, no count in any page, a page saying only whether one is the viewer's own. An older drawing posted through Yours takes its bookmarks onto the post; a post, a drawing or an account goes with its bookmarks, in code (`social_bookmarks`, a migration of the table and its indexes alone). A COMMENT TOO (the comment thread, step 3): "Bookmark" first in a comment's ⋯ ("This comment"), the post's toast and Undo (`posts.js` `window.SocialMark`, which `comments.js` calls), signed out "Bookmark this comment?"; kept in the Bookmarks tab as its card, the way to it above (`comments.world_cards`); `/social/c/<id>/bookmark` by the comment's rules (`reposts.comment_open`); a comment that goes, or keeps its place, takes its bookmarks, in code (`social_bookmarks.comment_id`). | `verify_socialbookmarks.py`, `verify_socialprofile.py` (15, the tab and the line), `verify_composer.py` (6, the move), `verify_socialauth.py` (14, the chain) |
| Pin this post at `/social` (`social/pins.py`, `_post.html`'s ⋯, `posts.js`, `profiles.py`; the owner's "all yes" to the Pin mock's A and A, Nov 25; part two of the map, its item 9; docs/SOCIAL-SITE.md section 40): "Pin to your page" in the ⋯ of your own posts, after Bookmark, its pin drawn in our pen, 44px and painted; "Unpin from your page" once it is the one; none on anybody else's post, a comment or a drawing shown outside a post. ONE AT A TIME (`social_pins`, unique on the person): pinning another puts the first back in its place, the site's toast saying so, with Undo, which puts back what was. FIRST ON YOUR POSTS TAB with a small "Pinned" line where "You reposted" would be, for you, for anybody who visits and for nobody signed in, shown once and the rest newest first, by the tab's own rules (a block either way, or anybody taken down, and it is not there; a post taken down, to its author alone); the tabs unmoved, Home unchanged. Signed in, not taken down, on a post of your own not taken down, with the token and Origin, 120 an hour; your own taken away whatever became of the post. A post takes its pin, in code, and an account its own with its posts. | `verify_socialprofile.py` (22, with SQLite's cascade off on a copy), `verify_socialauth.py` (14, the chain) |
| Draw back, two hands at `/social` (`social/drawback.py` two_hands, own, view; `posts.py` hands_states, hands_drawing, hands_picture, drop_post_hands; `post.html` and `_post.html` hands_views and hands_note; `posts.js`; Skribl's `line_of` and the player macro's `api` and `poster`; the owner's "all yes" to the Two Hands mock, Nov 25; docs/SOCIAL-SITE.md section 41): BEHIND THE OWNER'S SWITCH (`SKRIBL_SOCIAL_TWO_HANDS`, off by default: every draw-back joined as before). On, a new draw-back's drawing is his strokes alone, as drawn, on her paper and shape, no picture or music of his; it points to her drawing as it was; the picture of both and the line of both are kept beside it (`social_two_hands`); his own drawing rests on his lines alone. Her drawing shown to the viewer: Both, from the site, as a draw-back always played (hers squeezed to three seconds, then his), resting on the picture of both; on its own page the one pill under the drawing, Both · hers · his, each its own player, the box where it was. Removed (deleted, or taken down): his strokes alone from Skribl, "Ana’s drawing was removed". A block either way: his strokes alone, "The original isn’t shown to you". Not drawn back on yet ("hands"); draw-backs from before untouched; her post deleted lets go of its draw-backs and takes what is kept beside them, in code. The in-post player's bytes do not move. | `verify_socialdrawback.py` (15, a second server with the switch on; with SQLite's cascade off on a copy), `verify_hostseams.py` (`line_of`), `verify_socialauth.py` (14, the chain), `verify_inline.py` (the ratchet) |
| Drawn letters at `/social`, the server (`social/letters.py`; `social_letters`; `app.py`'s policy; Skribl's held states, `set_visibility_values(..., held=)` and `visibility_held`; the owner's yes, Nov 26; docs/SOCIAL-SITE.md section 44): only two people who follow each other write, nobody across a block, neither taken down. A letter is a row of its own, never a post; its drawing is Skribl's with the site's held visibility "letter", read by its two (on their side, no block between them) and by an admin once reported, nobody else; Skribl's posting API refuses the state and no author can PATCH into or out of it. Never listed anywhere. Written back on: theirs squeezed to three seconds, then yours at your pace (`drawback.join`), the hand's start kept. No photo, music or Flip yet. Opened only by the recipient's POST; taken back by its sender until opened; deleted from a side, gone once both have; reported by its recipient alone; an account deleted takes its letters both ways. A nudge under its own switch, Letters, on by default. Written in the Pad (`letters.js` `SocialLetters`; Skribl's `composehost.say`): Send, the pill, the drawer and the door to Flip aside. The pages: Write beside Following only between friends; the envelope by the bell and Letters in the desk rail, each with its dot; Letters' rows (a new one sealed); the two of you (draws itself once, opened as it plays, the hand-off mark, one Write back and New letter, each sheet's ⋯). | `verify_socialletters.py`, `verify_hostseams.py` (the held seam), `verify_socialpush.py` (the switch), `verify_socialauth.py` (14, the chain) |
| Reposts and quote posts at `/social` (`social/reposts.py`, `_post.html`'s row and `#repostSheet`, `_gallery.html` `quote_card`, `_quote.html`, `posts.js`, `compose.js`; the owner's "All yes", Nov 14, to the reposts mock; part two of the map, its item 3): THE ROW is 💬 · the repost · the heart · ⋯ (Open › removed Nov 19, the owner's "completely remove open": a tap on a card's own ground opens it, and its time is the link), Share… and Copy link in the ⋯; the repost the two arrows and how many reposts and quotes, counted by the viewer, none at zero, 44px, lit in --accent-ink once yours (3:1 and more off the paint, light and dark); three counts in the hundreds fit a 402px touch phone, read off the paint (the counted three give, never below 44px). A tap raises `#repostSheet`, the ⋯'s shape: Repost or, yours, Undo repost, each with its second line, and Quote; a drawing shown outside a post Quote alone, and to its maker Post it first (the composer with it attached, `compose.js` post; the owner's A, Nov 24); signed out "Repost this post?". Repost lights and counts at once, the count fading and the button growing round the arrows on every frame (none under Reduce Motion), one request at a time a post, no toast. Signed in, not taken down, on what is open to them (`comments.On`), the token and Origin, 120 an hour; one a person a post; your own always undone. A REPOST IS THE ORIGINAL'S CARD with "Mira Lopez reposted" at its top ("You reposted"), on Home's Following (the people you follow and you) and the reposter's Posts tab, merged newest first under the one cursor; Everyone posts only; the same post twice in a page once, the newest; on Home never by or of somebody muted; never anything a block hides or taken down. A QUOTE is a post (`is_quote`) with the original small inside it (name, @handle, words two lines at most, its drawing as the Gallery's still picture with "drawn in", one link to it), inside a post's card a well (`--quote-well`, a clear lilac and no line, the owner's "d2 is good", Nov 16, a chosen lilac since No dinge; on its own page the raised card), and an original with no drawing of its own that is itself a quote shows the drawing it leads to, however deep, until a post its viewer may not see (`reposts.Quoted` leads; A, the owner's "all yes" to "Just a Border", Nov 16); words alone are a post (`skribl_id` empty); the composer's Quote shows it small under the words, Post waking with words or a drawing; Make opens it without. Gone or hidden from the viewer, "This post is gone.". Activity: "Mira reposted your post" (to the post, grouped as likes), "Rook quoted your post" (to the quote, its words), the arrows on the face; never the dot; nobody muted. A post, a drawing or an account takes its reposts and lets go of its quotes, in code (`social_reposts`, the posts' four quote columns; a migration of the table, columns and indexes alone, its constraints NOT VALID on PostgreSQL). A COMMENT OR A REPLY TOO (the comment thread, step 3; the owner's "All yes" to A Comment Shared, Nov 17): its row is Reply · Repost · the heart · ⋯, the post's repost and sheet; reposted, it is a card of a post's shape on Home's Following and the reposter's Posts tab, with the way to it above (A: `_comments.html` `the_way`, its faces over the card's, the thread's line meeting the card's face at its edge), drawn only while its page would show it to the viewer (`comments.seen`), read with the posts' reposts in one query (`reposts.reposts_before`); quoted, its small card says "On Ben’s post" under the name, and once it is gone "This comment is gone." (`quoted_comment_id` 0, `reposts.GONE_COMMENT`: the column has no foreign key, a cycle); one the person may see, nothing taken down on the way, never a place (`reposts.comment_open`); Activity "Ana and 2 others reposted your comment" and "Cyd quoted your comment", never the dot (`activity.QUIET_KINDS`); a comment that goes, or keeps its place, takes its reposts and lets go of its quotes, in code (migration `36a8b352b347`; going down refuses while any is there). | `verify_socialreposts.py`, `verify_socialposts.py` (4, 11: the row), `verify_composer.py` (9, the quote path), `verify_socialactivity.py` (3), `verify_socialfollow.py` (8), `verify_socialprofile.py` (16), `verify_socialauth.py` (14, the chain) |
| DRAW BACK at `/social` (`social/drawback.py`, `posts.py` `post_drawback`, `_drawing_back` and `drawbacks`, `_post.html` `drawback_pen` and `drawn_on`, `compose.js` drawBack, Skribl's `lib/drawback.js`, `composehost.js` underlay and `read_payload`; the owner's "All yes", Nov 19, DECISIONS.md "Draw back, mocked"): the pen after the heart under a post's drawing of one page, signed in, 44px, how many draw-backs beside it; it opens the composer and the Pad over it on the original's shape and paper, the original faint under the pen in its own colours (0.32, one coat), "Drawing back on Ana’s" and Theirs (faint, full, hidden). THE SERVER JOINS THE TWO from the original as Skribl stores it, never as a browser says it was: hers first as she plays, squeezed to three seconds when longer, then his at his own pace, on her shape and ground, her takes then his; her photo and song kept (the author's background and music; `read_payload`'s `inline_media` where a store keeps them), the answer's own photo or music, an answer on another shape or a page short, a Flip that loops, keeps a page under or plays to a beat refused with why; a post not there, or behind a block (held by the site and by Skribl's own read), as gone. A draw-back is a post (`is_drawback`, `drawn_on_id`, `drawn_on_owner_id`, SET NULL when hers goes; migration `d7a3b19e4c20`); its card says "Drew back on Ana’s" (her post the link, 44px), her face small at the foot of his, and once hers is gone "Drew back on a drawing", his playing on with both hands. WHAT IT SAYS OF ITSELF (Nov 19, the walkthrough's mocks, choice 6): each hand's own drawing time is kept when it is made (`hands_json`, in whole seconds, the original's hands first; migration `f2a6d4c81b57`), and its line says them ("Drawn in 15 sec + 5 sec", never the joined drawing's own time, in which hers plays squeezed; past three parts the whole and how many people), its play button who and the whole ("Ana + Theo · 20 sec"; past four names "Ana + 4 others"), a Gallery tile and a quote's small card the whole; nobody is named to a viewer any hand is hidden from (gone, taken down, a block either way), nor once the drawing it answers is gone, nor on your own drawing; one from before the hands were kept is said from the two drawings' stored lines while its original is there. Skribl's player is handed the numbers in `line_info` (`parts`, `people`, `by`; docs/INTEGRATION.md) and writes `by` as text. ON HER POST'S OWN PAGE (the Calm Post Page, Nov 20): "Draw back" in words is the answer bar's, on every post that can be drawn back on; the draw-backs on it are a strip under a small quiet label ("3 draw-backs"), each tile the joined drawing cut out of its share card, and with none there is no strip and no heading; when the replay ends there Watch again rises alone on the drawing and the bar's Draw back lights up (a card on Home keeps both pills). HER SAY (the owner's "All yes to everything", Nov 20; `docs/SOCIAL-SITE.md` section 24): on her own post each tile of the strip wears her Gallery tab's eye beside the name (`eye.js`, hers alone, not in anybody else's page or source); one tap hides that draw-back from her post for everybody (`drawn_on_hidden_at`, migration `a4c9e1b7d352`; `/social/p/<id>/shown`, the original's maker alone), counted for nobody, her label saying what everyone else sees and one line how many are hidden; it stays its maker's post everywhere else, nobody is told, nothing is deleted, and Undo or the eye brings it back. SEE ALL (the owner's "C", Nov 27; `docs/SOCIAL-SITE.md` section 53): past the strip's twelve (`posts.BACKS`), "See all" on its label's line opens the page of every draw-back (`/social/p/<id>/draw-backs`, `drawbacks.html`; Load more from `/social/p/<id>/draw-backs/more`), the strip's tile (`_backs.html`) in a grid, two across on a phone and four on a desk, twenty-four at a time; one read for the strip and the page (`posts.backs_on`), and her eye's counts one fewer or one more from what the page said. AND WHO CAN DRAW BACK (the same yes; `docs/SOCIAL-SITE.md` section 25): a post's maker says Everyone (where every post starts), People I follow or Nobody (`drawback_by`, migration `c8d3f5a1e694`; ONE RULE, `posts.open_to`: she always can on her own, "follow" is whom she follows now), in the composer (one quiet line under a drawing that can be drawn back on, "Anyone can draw back · Change", opening Settings' pill where it stood; `compose.js` whoOpen and `drawableHere`) and in her own post's ⋯ (a card with the pill, a tap the change; `posts.js` whoSet, `/social/p/<id>/drawback-by`), with one quiet line on her own post's page while it is not Everyone; the words are `_who.html`'s alone, the pill outside Settings is `social.js`'s `SocialSwitch`. Somebody who can't has no pen at all (row, answer bar, replay's end) and nothing says why; both doors refuse a stale page kindly (403 `drawback_closed`). A FLIP, PAGE FOR PAGE (the owner's "all yes", Nov 25, to the Flip Draw Back mock; DECISIONS.md, "Flip's Draw back, page for page: built"): the pen on a Flip's card, and the composer opens Flip over it (`compose.js` `pagesOf`), one empty page of his for each of hers at her timing, on her shape, paper and picture, her page faint under the page he is on and her pages faint in the strip; what would add, move or delete a page or change her timing refuses, every way in (`flip.js` `dbHeld`), and so does the eraser; the site joins the two page for page, her page with his on it (`drawback.py` `_join_pages`), or keeps his pages alone behind the owner's switch (`_own_pages`). A page that draws itself plays hers, then his (the owner's answer, Nov 25). Not yet: a Flip that loops, keeps a page under or plays to a beat (no pen, `undrawable` says which; a Flip posted before keeps its pen, answered when opened). RECOLOURS (the owner's "all yes", Nov 25, to the Recolor mock; `docs/SOCIAL-SITE.md` section 43): a drawing with recolours is drawn back on (one that said "recolors" keeps its pen); Recolor works while drawing back, on his lines only (hers lie on a layer of their own), a tap on hers saying whose it is ("That line is Ana’s. Recolor changes yours."; `lib/drawback.js` `hers`) and the lens showing hers faint (`under`); the join keeps each hand's recolour moments to its own lines (`drawback.py` `_moments`: his line, count and gesture moved past hers), and two hands keep his as he made them. | `verify_socialdrawback.py` (6, the bar's Draw back, the strip and See all; 7, the replay's end; 8, what it says; 11, her say: hiding; 12, her say: who can draw back; 16, a Flip page for page; 17, recolours), `verify_inline.py` (a drawing of several hands; the embed's bytes), `verify_socialauth.py` (the chain's indexes) |
| HOW IT WORKS at `/social/how` (`social/how.py`, `how.html`, `how.js`; the owner's "All yes", Nov 19, to a door from the site to How it works: "first row on a phone, above Settings on a desktop, and there for visitors too", opening "Blooby's own short page, with Pad's and Flip's help at the bottom"): the ☰'s FIRST ROW, and on a desk a tab in the rail above Settings (above Sign in before that), lit on its own page; a phone's bar keeps its four places. The page is the site's own, for anybody: Watch an example (three drawings in Skribl's in-post player, FILES NOT POSTS so they are there on a site with no posts: Skribl's cat and bouncing Flip, and the site's own draw-back, `static/how/drawback.json`, that cat and an answer drawn through the composer's Pad; each box its drawing's shape before the drawing comes; each play button what its file says, the draw-back's both hands' time; the first draws itself once, never under Reduce Motion; one line and Try again when the files do not come), People often ask (four rows, a tap going where it is done; a visitor's the same lines with nothing to tap, and Sign in beside one line that says why), The drawing tools (the Pad's and Flip's own How it works: signed in, THE EDITOR INSIDE A POST with its help showing, `SocialComposer.editor`, the same way in as a draft's tile, so nobody is sent out of the site; a visitor, the editor's own address with `?help=1`). SKRIBL'S SIDE, one module for both editors (`lib/ask.js`): `?help=1` opens How it works once the page has loaded and leaves the address; a host's composer asks the editor it holds with `skribl:compose:help` (`editor_compose.js`). Every word 4.5:1, every row and button 44px. | `verify_socialapp.py` (11; 4 and 6 for the ☰'s rows), `verify_ask.py` (6), `verify_socialsettings.py` (the ☰'s rows), `verify_social.py` (2 and 8: the rail, the layers), `verify_socialactivity.py` (the rail) |
| JUST A BORDER at `/social` (the owner's question, Nov 16: "are there any other places where you just have a border around something with the same color as the background that it is sitting in"; "all yes" to the mock): no box with something in it is set apart from what it sits on by its line alone: its fill differs from the ground round it by 1.08:1 or more, or it wears a lift. The second button and every switch's track wear Skribl's lilac in both themes (`--btn2-bg`; solid since No dinge, #e7e0ff light and #332a58 dark, 1.13:1 to 1.27:1 from every ground); Home's, the Gallery's and the theme's switches are one switch (`.fo-seg` on the second button's tint and line); inside a post's card a quote is a well (D2). Not counted: a lift (since the crisp build, Nov 20, one line of shade under the edge; a ring alone is none), a drawing's plate or anything on a picture, a dashed "add" outline, fields. | `verify_socialreposts.py` (13, the census of the site's pages, phone and desk, light and dark; 7 and 11, the quote), `verify_socialfollow.py` (2, 7), `verify_socialsettings.py` (1, 6) |
| NO DINGE at `/social` (the owner's words, Nov 16: "I want everything to pop, crisp and luxurious.. no dingy"; "All yes" to the no-dinge mock): a second button (`.btn`, the boxed icon buttons, the comment button, Make's Draw / Flip / Yours), a switch's track, a quote's well and a placeholder (an empty face, Activity's picture slot, a drawing's plate while it loads, `--draw-wait`) each wear one chosen colour, solid, never a see-through wash that takes the grey of what it sits on, and read as lilac (OKLCH chroma 0.038 and up for a button or a track, 0.02 for a well, 0.03 for a placeholder; 0.07, 0.045 and 0.06 in dark). Make's Post, waiting, is crisp: the second button's lilac in the chosen violet, never faded. Notes, highlights and an icon's disc (`--tint`: a note, a comment or Liked by you came to, the @ list's chosen row, the rules page you're on, the passkey's, the Home Screen steps', Make's) wear the second button's lilac too, solid since the leftovers (Nov 17). | `verify_socialreposts.py` (13, no dinge: the same pages, phone and desk, light and dark, every role seen, a note and a disc among them; 11, the well paints its own colour), `verify_composer.py` (3), `verify_socialcomments.py` (33), `verify_sociallikes.py` (9) and `verify_socialactivity.py` (7): a landing glows in the solid tint |
| JUST A BORDER in Skribl's editors, the Library and the Gallery (the owner's "Yes to all", Nov 16, to the editors' mock; the row above is the same rule on the site): a tip in How it works is a well (the site's `--quote-well`, #f0ecff and #16112b since No dinge, no line); a second button and a switch's track wear Skribl's lilac in both themes (`--btn2-bg`, the site's value for value, solid since No dinge, `--btn2-hover` under a pointer): Make another, Keep drawing, Tap the beat, Hear the restart, Flip's page and selection bars (`.pb`), the drawers' panel buttons, Retry, Try again, Keep for later, and the Library's Copy link, Share, Copy key, Save file and Undo; Flip's speeds, This page / After, the fine-tune step on a door's card, the Library's two switches and the Gallery's New / Hot (`.seg-track`, `segslider.css` `--seg-track`). Each set apart from what it sits on by its own fill, 1.08:1 or more, its words keeping TWO INKS' 7:1 through the tokens (one chosen ink, `--seg-on-ink`; one second ink), a page bar button switched on in the chosen ink, the Library's row buttons' words in the first ink (A, A, A: the owner's "Yes all", Nov 16). A switch on the menu's paper stays a white card (ONE LOOK ON THE PAPER); sheets, drawers and menus float with a shadow; dashed drop zones and fields are not counted. | `verify_contrast.py` (just a border, the editors: every role on Pad and Flip, light and dark, phone and desk, every role seen), `verify_galib.py` (11) |
| NO DINGE in Skribl's editors, the Library and the Gallery (the owner's "All yes", Nov 16, to the no-dinge mock; the site's NO DINGE row is the same rule): the second button and every switch's track one chosen lilac, solid (`--btn2-bg` #e7e0ff light, #332a58 dark; never a see-through wash that takes the grey beneath it), Flip's Duplicate, Blank, Tween and Smear (`.addcol .addbtn`: an older rule there outranked the first fix), its offset readout, the recovery key's buttons, the leave sheet's Keep drawing, Copy delete key (on the Post sheet's key row, the sheet's card since the last round), Load more and the Gallery's Cancel and Retry on it too; on the Library's playing row a shade up; a tip's well and the tips' counts lilac (`--tip-well`, `--count-fill`); toasts, Flip's chip, the save status, the hints, the other-tab notice, the zoom readout, the eyedropper's bar and the replay's speeds clear glass (`--chip-glass`, `--chip-line`, `--chip-lift`: white with a lilac edge in light, violet in dark), a second button on it a step up in dark (#45397a: the glass lets the drawing through; the eyedropper's Cancel too), Flip's frame clear; the Re-add card the paper's card with the amber on its edge; a draft's picture slot the site's `--draw-wait`; the Pad's Post, waiting, the second button's lilac in the chosen violet; a page bar button, undo and redo, the Pad's and Flip's alike, and the song timeline's zoom, undo and redo, when off at full strength with quiet words (`--off-ink`); a How it works header and a menu row under a pointer Ask's rows' faint lilac, never the control's grey. The last round (the owner's "All yes", Nov 17): the player's round buttons (the link page's, and the way into full screen on the Pad's line and Flip's speed row) the lilac, the link page's one-pixel line mixed over it (Increase Contrast strengthens it), a lit toggle among them the pressed look (`--press-fill`, `--press-ring`); the scrub's track the lilac on the page, its wash kept in full screen (a rule on the scrubber, not its frame's every track, which took Flip's line); the song's − and + the lilac, and its hover; the icon discs in How it works and Export the site's disc, the mark in `--accent-ink`, an open section's a step up; Flip's page bar the strip's own paper and its pages' badges the toasts' clear glass (an armed ✕ keeps its red); the Post sheet's key row the sheet's card. | `verify_contrast.py` (no dinge: every role the just-a-border row reads, solid and lilac enough; a control painted the drawers' paper's own card is the tiles' white card, not asked for lilac), `verify_galib.py` (11), `verify_parity.py` (Flip's off Undo and Redo the Pad's), `verify_surfaces.py` and `verify_theme.py` (each colour a token), `verify_newundo.py` and `verify_drafts.py` (a second button on the glass stands apart from it, painted, both themes), `verify_replayspeed.py` (the link page's round buttons, Loop on, its track), `verify_linkpage.py` (their one-pixel line), `verify_watchfull.py` (the way in; the Pad's track on the page, and each full screen's kept), `verify_fullsmart.py` (the link page's full-screen track), `verify_musicdoors.py` (the − and +), `verify_help.py` and `verify_exportui.py` (the discs), `verify_pages.py` (Flip's page bar and badges), `verify_ux.py` (the key row) |
| CRISP at `/social` (the owner, Nov 20: "I want to minimize shadows to create depth and keep it crisp and luxurious. Shadows seem blurry and kind of muddy the page"; "All yes" to the crisp mock's B): depth is THREE HEIGHTS and a soft shadow (over 2.5px of blur) is only for what floats. ON THE PAGE (a post's card, a comment's bubble, a tile, a panel, the answer line, the comment box) the edge and one line of shade under it, 1px with no blur (`--card-drop`; in dark a line of light inside the top); IN A CARD (the drawing in a post's card, a bubble, the comment box) the edge alone (`--draw-lift`); FLOATING (a toast, the list under an @) the one shadow, short and close (`--float-drop`), a sheet a line of light along its top and no shadow (`--sheet-top`), the play pill a hairline and 1px/2px (Skribl's `inlineplayer.css`); THE FILL enamel, no glow (`--fill-drop`). Nothing painted at rest is soft (the replay's pen nib aside), and `social.css` declares no soft shadow but the two that float. A new surface gets an edge first; before adding a shadow, count. AND THE EDGE HAS TO BE CLEAR ENOUGH TO DO THE WORK ALONE, IN DARK TOO (the owner, Nov 21: "now it looks less crisp in areas"): dark's `--card-edge` 26% of the lilac over its card and `--card-line` 0.26 (each was 12 while shadows carried them), a card's edge 1.4 to 1 or more from the card and from the page in both themes. | `verify_socialposts.py` (23: the painted count on five screens, the three heights, what floats, every shadow the sheet declares; 17: a tile's and a drawing's lift is the one line, and a card's edge off the paint against its card and the page), `verify_socialreposts.py` (13: a lift is a soft shadow or a line a pixel or more down; a ring alone is none), `verify_socialmentions.py` (4), `verify_inline.py` (the pill's bytes, named beside the ratchet) |
| CRISP in Skribl's editors, the Library and the Gallery (the same "All yes": "the Pad and Flip next, the same rule, both together, their buttons' text shadow with it"; the row above is the same rule on the site, value for value): a card on a sheet its edge and one line (`--menu-card-drop`); the glass (a drawer, a sheet, Flip's page strip) its rim and one close line, 1px/2px (`--glass`); what floats (a toast, a chip, a hint, and since Nov 21 the three pops that open OVER THE DRAWING: the tray of tools, the shape picker, Flip's stamps shelf) the one shadow (`--chip-lift`); Post, and Record while recording, enamel with no glow (`--fill-drop`), the white words on a purple button with no text shadow. `pagemenu.css` restates the glass and the card for the Gallery and the Library and moves with them. A POP'S POINTER IS PART OF ITS OUTLINE (the owner, Nov 21: "The little V at the bottom disappears with no shadow or border"): a square of the pop's paper turned to a point, the paper's edge along its two lower sides, placed by `--pop-point`. AND IN DARK THE EDGE IS CLEAR ENOUGH TO DO THE SEPARATING: `--menu-card-line` 0.26 and the two edges 26% (they were 0.12 and 12%, set while soft shadows did the work). AND THE LAST SOFT SHADOWS WENT (the owner's "All yes" to Four Looks' 2, Nov 22): a sheet that rises or opens in the middle wears the glass's rim and close line (`--glass`), what floats over the drawing its edge and the one shadow (`--chip-lift`; a desk's tooltip too, on every page it shows), a video in a card its edge alone, a light a rim of its own colour. What keeps its own is listed where the check reads it (`CRISP_KEPT`, which only shrinks): a knob's tiny shadow, the canvas's inner shade, a replay pen's light. | `verify_contrast.py` (CRISP, THE EDITORS: nothing soft painted on any surface it opens but what floats and that list; the three heights; what each former soft shadow wears; Post and Record), `verify_galib.py` (3: the two pages' lift, value for value with the Pad's; and their menus' edge with the Pad's, painted), `verify_linkpage.py` (a ring is measured along the side it is read on), `verify_tray.py` (the tray's pointer, its shadow, and both read off the paint on Flip at a phone's three pixels to one, light and dark) |
| A TILE FOR EACH DRAWING at `/social` (the owner, Nov 20, of the Gallery in dark: "each row distinct"; then Nov 21, of it in light: "I like the colors that make rows. Maybe they should be individual tiles, not rows", and yes to the mock's A): under every drawing of a grid of tiles and its name one flat tile (`--row-band`, on a sheet's paper `--row-band-sheet`; `--tile-out` round the picture, 6px, 4px in Make's list), no blur, 8px of the page between two tiles across and down, a last row that is not full its tiles and nothing more; wherever the one grid is (the Gallery, a profile's Gallery and Drafts tabs, the front door, Make's list). ENAMEL SINCE NOV 26 (the owner's "Yes to B, with their lavender edge", to the Enamel Tiles mock): the tile white in light and obsidian (#171723) in dark, on a sheet too, a step of 1.03 to 1.13 from the page; flat; their lavender edge drawn inside it (`--tile-edge`), alone and in whole screen pixels since the evening's crisp edge (`--tile-line`, as near 1px as each density allows: one pixel at 1x, 1.25x and 1.5x, two from 1.75x, three from 2.625x; the line of light and the dark foot gone, the owner's "All yes on A"); no shadow round it. UNDER A MOUSE ON A DESK (the owner's "All yes" to the Tile Hover mock, Nov 26) its edge takes the site's hover line (`--tile-hover`: `--btn2-line`, a face tile's and Make's door's; with "more contrast" the accent), fading in; it does not grow, and a phone is unchanged. | `verify_socialposts.py` (22, read off the paint, each point with the tiles and without; the edge where it is painted and nothing beside it, and in whole screen pixels at seven densities; the hover on a desk, light and dark, and a touch phone unchanged), `verify_socialsettings.py` (15, the hover under "more contrast") |
| THE TALK CLOUD ANSWERS at `/social` (the owner, Nov 21, of Bluesky's reply screen: "Is that what we're going for?"; yes to the mock's B): on a post's own page the cloud in its row is a button that opens the comment box as the bar's line does, comments or none (a phone's sheet with the post's own words under its title, a desk's box, signed out "Say something?"), focus back on the cloud after; on a card it is a link to the post with its box open for somebody signed in (`#say`), to the comments signed out; the number beside it follows what is said and deleted on the page. One meaning, under a post as under a comment. | `verify_socialcomments.py` (34; 30 and 32: the quote; 11: the cards), `verify_socialposts.py` (10, 11), `verify_socialreposts.py` (16) |
| THE PERSON'S TAP STOPS AT THEIR NAME at `/social` (the owner, Nov 21: "Right now profile tap extends past name. It should stop at name"): on a card and on a page of its own the person's link is as wide as the longer of their name and @handle, 44px at the least and a finger tall, and the room beside it is not the person's (a card's opens the post; a page's does nothing). No second link for the @handle: it reached down over a post's first words. | `verify_socialposts.py` (10, 11), `verify_socialreposts.py` (16), `verify_socialcomments.py` (49: a page's own head) |
| NEVER STRANDED at `/social` (the owner, Nov 20: "there's no back button on so many screens. You end up stranded a lot"): every screen the bar does not lead to has an arrow at its top's start with its own name beside it, and the arrow goes WHERE YOU WERE when that was this site (`social.js`: the browser's own Back), else to the screen it belongs to; Home, the Gallery and your own profile have none; a door screen keeps the mark in the middle (its INK, not only its link) with the arrow at the top's start; a desk shows no arrow. A WRONG ADDRESS under the site is a kind page with the bar and a way home (`lost.html`, the site's own route `social.lost`), to a person going there; a script's ask and every other verb read the bare 404 they read before. AND A PAGE THE ASKER MAY NOT KNOW IS THERE (Invites, Your reports, to anyone but an admin) IS THE SAME ANSWER AS AN ADDRESS THAT WAS NEVER ONE, word for word and header for header, to a browser and to a script: change one and the other moves with it (`_not_here` in `social/__init__.py`). | `verify_socialposts.py` (21), `verify_socialcomments.py` (40), `verify_socialauth.py` (6: Invites and Your reports beside a page that is not there) |
| A DRAWING'S BOX IS ITS OWN PAPER TO ITS EDGE at `/social` (the owner, Nov 21: "Look at the canvas border. Is that we are doing?"; then "The drawings edge is A"): the box round a drawing wears the drawing's own ground (`--plate-ground`), so there is no band of the waiting colour between the picture and its one line; the waiting colour (`--draw-wait`) only where a drawing has not come or its ground cannot be said. THE SITE tells the box where it made the page (a post's card and page, a drawn comment's bubble, page and card: `_post.html` `own_ground`); THE PLAYER tells it where the page was never told (a draft in Make and in the comment box, How it works' examples: `social.js` `SocialGround`, a colour and nothing else) | `verify_socialreposts.py` (20: the paint, five places; 13: a drawing's own paper is no placeholder, the waiting colour read as itself), `verify_composer.py` (4), `verify_socialcomments.py` (14), `verify_socialapp.py` (11) |
| Mentions at `/social` (`social/mentions.py`, `mentions.js`, `_mentions.html`, `_mention_face.html`, `said()` in `_post.html`, `post.html` and `_comments.html`; the owner's "All yes", Nov 15, to the mentions mock; part two of the map, its item 4): AN @HANDLE THAT IS SOMEBODY, in a post's words, a comment's or an answer's and a quote's own, is a link to their page in the small violet ink (--accent-ink, 600, never underlined; 8.26:1 on the card light, 8.39 dark, 7.75 and 9.89 on a comment's ground), the words' own size and line, so nothing else in them moves (the words' box one height with it and without); one that is nobody, and every one past the first ten people in one post or comment, stays words; the words escaped first, only the handles kept as mentions made links; plain where the words are one link already (Activity's peek, a quote's small card). A card's words are no link of their own now (a link can't hold links): a tap on them opens the post as the card's ground does, a tap on a mention the person, never the post, a drag that selects them nothing. KEPT AS TYPED, BY WHOM: `social_mentions` (who, the handle as typed, by whom, in a post or a comment, exactly one, a CHECK; whose; when), written in the same transaction as the post or the comment by every way words are written (a post, a quote of words alone, an older drawing posted, a comment, an answer), never changed after (nothing can be edited); the link goes to the person by id, so a handle that changes keeps old mentions working; old words with an @ in them stay words (a migration of the table, its indexes and the names' index alone). Read once a page for all its cards, and once for all its comments; a tile reads none. THE LIST UNDER AN @ (`/people/suggest`, signed in, 600 an hour): in the composer and a comment's box (answers too), from the @ on, right under the line being typed (8px), placed over what is there (nothing moves, the sheet is not pushed), opening over the line where there is no room under it (a phone's comment sheet on its keyboard), so above a phone's keyboard; the people you follow first (their handle or any word of their name), then anybody whose handle or name (any word of it, since finding people) starts with it, by name, four at most, each read on an index (with letters, your follows and their ways and everybody's ways, `social_people_words`, as the Gallery's search reads them; for an @ alone, your follows, the handles' and the names' `lower(display_name)`); nobody a block hides either way, nobody taken down, never yourself; the mock's card (--card, --card-line, 16px round) and its 52px rows (the face 36, the name 17px 600, the @handle 15px); a tap (or Enter or Tab on the highlighted row, the arrows moving it, Esc closing the list alone) puts "@handle " in where the typing was, the field keeping its focus; a listbox of options, the field's aria-expanded and aria-activedescendant; a fade in, none under Reduce Motion; every field 16px or more. WHO IS TOLD: Activity, "Rook mentioned you", a row each, their words in quotes, the post's (or the comment's) small picture, their face wearing an @ (white on the follow badge's purple disc, 5.33:1), to the post or the comment glowing; it LIGHTS THE BELL'S DOT; never from somebody muted, never through a block either way, never yourself, never anything taken down or not shown (`comments.seen`'s rules); a comment on your post or answering you, or a quote of your post, that mentions you is one row, its own. A post, a comment (every way one goes) or an account goes with its mentions, in code. | `verify_socialmentions.py`, `verify_socialposts.py` (10, the words the card's ground), `verify_socialactivity.py` (3, 9), `verify_sociallikes.py` (9), `verify_socialfollow.py` (9), `verify_socialauth.py` (14, the chain) |
| Blooby on the Home Screen at `/social` (`social/__init__.py` `manifest` and `shared_folder`, `SITE_GROUND`; `base.html`'s head; `_menu.html`'s two rows, `_homescreen.html`, `social.js` `homeScreen`; `social/static/blooby-icon-*.png` drawn by `harness/tools/blooby.py site-icon`; the owner's "All yes", Nov 15, to the Home Screen mock; part one's step 7): every page of the site's links `/social/manifest.webmanifest` (Blooby, opening on Home, standalone, the dark `SITE_GROUND`; its scope the folder the site and Skribl's pages share, so the Pad, Flip and the Library open inside the app) and wears blooby.app's own icon (the owner's pick, Nov 13: waving Blooby on the lilac, no star, 0.82 of the side; within a pixel of `docs/brand/blooby-app-icon-*.png`) as its touch icon and page icon and where it shows Blooby in small (sign in, joining, recovery, the kind pages, Activity's empty state; the kind card imported with the page's context); both theme-color metas say `SITE_GROUND`. Skribl's pages keep Skribl's manifest and icons. The ☰ (a phone's) has Add to Home Screen right under Settings (Sign in) on an iPhone or iPad in a tab, opening the steps (the site's sheet, gliding up as the ☰ goes; iOS 26's three steps, "More" for the ⋯, the sign-in note; focus on Got it and back on the ☰), and where Chrome offers its install (asking Chrome once, its own bar kept away); Reload in its place from the Home Screen; a desk neither. Every word 4.5:1 and more off the paint, light and dark; the row as tall as Settings; every target 44px. The Pad's and Flip's steps say iOS 26's too. THE SPLASH (`splash-boot.js` in the head before the first paint, `splash.js`; `brand/blooby-splash-jump.webp` drawn by `blooby.py splash-jump`, the word the site's hello; the owner's "All yes, B with the stage spotlight", Nov 15): only the Home Screen app, once a launch, never a tab (which never downloads the strip); the night ground and the bar's night from the first paint, no stars; once both pictures are here, a still spotlight of the icon's lilac comes up on Blooby, who jumps (seven poses, lifted 96px, his shadow on the pool; the last pose without sparks) while "blooby." writes itself under the stage the first time and its blush falls as skribl's i-dot does; his outline 4.5:1 and more against the light at every pose; a tap skips it, Reduce Motion keeps him still, a picture that does not come never holds the page, the page's own drawings wait for it. The site's hello for the Pad and Flip at blooby.app falls the same way. THE APP'S TOP EDGE: in the app (`is-app`), 6px of the page's ground fixed at the top, so iOS 26 lays no glass blur over the header. | `verify_socialapp.py` (8, the splash; 9, the top edge), `verify_hello.py` (the site's part), `verify_socialactivity.py` (9, the empty state's icon) |
| THE BAR STAYS AT THE SCREEN'S FOOT at `/social` (`social.js`, the part of that name; `compose.js`'s Post; the owner, Nov 21, from the Home Screen app: "When I scroll the bottom menu scrolls too?"): an iPhone's own fault (after its keyboard has been up it can go on taking the foot of the screen for covered, and everything pinned rides the page until the app is opened again), so every page of the site watches for a visual viewport left short of the window, or offset in it, with nothing being typed, and asks the phone to measure again: one pixel of scroll and back, once the page has rested. Never while words are typed, with the page pinched larger, with a finger down, on a desk, or on a page that cannot scroll; three times at the most for one stuck spell. And the keyboard is put away before the app changes page (Post as it is pressed, a form that really goes, the page going); a search that stays on its page keeps it. No stylesheet rule can undo the fault: do not move the bar for it. NOT SEEN ON AN IPHONE: the suite stands the fault in, and the owner's phone says whether the phone listens (`docs/SOCIAL-SITE.md` section 37) | `verify_socialapp.py` (12) |
| WHERE A TINT CANNOT SHOW, AN EDGE, at `/social` (`social.css`, the forced-colours block by the one pill; the colour audit of Nov 21, fix C; the owner's rule, "a ring only where a tint cannot show"): in forced colours, and only there, every option of the one pill (`.fo-seg`, `.theme-switch`) wears an outline and the chosen one the system's Highlight, as the rules' tab you are on and a list's picked row do; a chosen one reached with the keyboard keeps its focus ring outside it. AND NOTHING THE KEYBOARD REACHES IS UNDER A BAR (fix E): under 900px the page's own scroller keeps the bar's height clear when it brings a control into view, and the answer bar's too on a post's page (`scroll-padding-bottom` on the root; `docs/SOCIAL-SITE.md` section 38) | `verify_socialsettings.py` (12, 13), `verify_socialcomments.py` (50) |
| "MORE CONTRAST", ANSWERED, at `/social` (`social.css`: each ramp's `-hc` values and the `prefers-contrast: more` block after both dark copies; the colour audit of Nov 21, choice 5): for a device that asks, the grey words a step stronger and every edge firmer, light, dark chosen and dark by the device; nobody else sees it. AND A COPY IS ITS ORIGINAL (choice 6): every site token whose comment names one of the editors' or the Gallery's is that one's value, light and dark (`docs/SOCIAL-SITE.md` section 39) | `verify_socialsettings.py` (14, 15) |
| ONE SHARP PIXEL AT EVERY DENSITY (the colour audit of Nov 21, choice 1): `--hair` has a step for each density between 1x, 2x and 3x (1.25, 1.5, 1.75, 2.25, 2.5, 2.625, 2.75), in `styles.css` (and so `player.css` and `gallerysection.css`), `pagemenu.css` and `social.css`, so a 1px-scaled line is one screen pixel on a Windows screen at 125 to 175% and on 2.625 and 2.75x phones. A new place that sets `--hair` sets every step, or takes the body's | `verify_socialposts.py` (17) |
| THE EDITORS' COLOURS, ONE NAME EACH (the colour audit of Nov 21, choices 7, 8 and 10): the second ink's four other names point at `--text-secondary` and the violet's four roles at `--accent`, in both ramps; Undo and Redo with nothing to undo read 3 to 1 or more (light's `--off-ink` #9088b6); and no sheet or template asks for its letters to be thinned (`-webkit-font-smoothing`) | `verify_theme.py`, `verify_a11y.py` (11d) |
| A HINT IN A TEXT BOX CAN BE READ (the colour audit of Nov 21, fix A): every placeholder on the Pad, Flip, Skribl's Gallery, Library and feed is 4.5 to 1 or more on its own field, light and dark, read as painted (its colour times its opacity over the field's ground). None is left to the browser's grey (Chromium's `#757575` read 3.4 to 4.6; Safari's is another), and none wears the dim ink: each takes its page's second ink at full strength (`styles.css` `.post-input` and `.name-input`, `posted.css` `.reckey-input`, the Gallery's and the Library's own sheets). A new text box's hint is set the same way | `verify_a11y.py` (11c) |
| A WAITING LINE IS NOBODY'S (the colour audit of Nov 21, fix B): in the in-post player a drawing not yet played keeps its line of controls hidden (`.skribl-inline-line.is-waiting`), and hidden means from the keyboard and a screen reader too (`visibility: hidden`; no height and no opacity alone left four stops that showed nothing). Once it has opened, its controls are the keyboard's again. The 18 bytes are in the in-post player's ledger (`EMBED_RATCHET`) | `verify_inline.py` |
| EVERY TOKEN THE EDITORS' SHEET DECLARES IS READ BY SOMETHING (the colour audit of Nov 21, fix D: `--line-mid-2` was read by nothing and rode along in `player.css`, which is on a byte budget): a stylesheet, a template or a script, the derived sheets not counted as readers. A token nothing reads is deleted, not kept for later | `verify_theme.py` |
| Finding people at `/social` (`social/people.py`, `_people.html`, `explore.html`, `explore.js`, `follows.js`; the owner's "All yes", Nov 15, to the finding-people mock's A; part two of the map, its item 5): THE GALLERY'S BOX FINDS PEOPLE TOO ("Search people and drawings", to the eye and to a screen reader): with a search, People first (up to three, then "See all" when there are more), then Drawings as before; no search, the Gallery as it was; in the part that fades, so a search's people change only unseen, read on every frame; the pills change the drawings alone. A row is the mock's, 64px: the face 44, the name 17px 600 (--ink, 16.86:1 light, 16.56 dark on the page ground), the @handle 15px (--ink-2, 7.10 / 10.12), one link to their page from the row's start to Follow, and Follow as on their page (one sheet for every Follow on a page, saying the name of the one tapped; signed out, Sign in coming back to the search as it is); your own row has no Follow. WHO IS FOUND: anybody whose name, by any word of it, or whose @handle starts with what was typed, never the middle of a word; case, accents, a leading @ and anything not a letter or a digit put aside; the people you follow first, then by the word that found them, then who joined first; nobody a block hides either way, nobody taken down, signed out too; a mute changes nothing. SEE ALL (`?who=people`): the people alone, twenty a page, Load more in place, none twice, none missed, by a cursor naming no internal id; the back button kind. THE WAYS are rows (`social_people_words`, a migration of the table and its indexes alone, its key in the "C" collation on PostgreSQL), written in code with every name (joining, Edit profile: a name changed found by its new words, never its old), read on their indexes, the same few reads a page however many are found; the people already there filled in code (`flask social words --write`, once each start after the site's chain, gunicorn.conf.py). The list under an @ reads the same ways. | `verify_socialsearch.py`, `verify_socialmentions.py` (4, 9), `verify_social.py` (5), `verify_socialauth.py` (14, the table and the deploy's fill) |
| Search at `/social/search` (`social/gallery.py` search_page, `search.html`, `search.js`, `explore.js`; the owner's "Yes to all", Nov 22, to round two of the "Blooby and Search" mock): A PLACE OF ITS OWN, the magnifier drawn in the bar's pen. A phone's bar holds five places, Make in the middle (Home, Gallery, Make, Search, You), 77.2px each on a 402px phone; a desk's rail has Search right under the Gallery, Make the big button below. Two links in `base.html`, one shown at each width, so a keyboard takes the places in the order seen. Lit on its own page, its line heavier (2.9) at the same outside size; drawn 4.7% larger than the mock's so its ink reaches Home's (25.5px). THE PAGE: the ☰, the wordmark and the bell, as the Gallery's top; the Gallery's box; typed, what the Gallery's box finds (People first, See all its own, then everyone's drawings, newest first; no pills); nothing searched yet, one quiet line, "Find people and drawings."; before a search, RECENT SEARCHES: the words searched with the keyboard's Search (or that found something opened) and the people opened from it, newest first, ten at most, an × each and Clear all, kept on the phone alone (localStorage, a list for each person signed in and one for nobody), a recent search searching again in place; they come and go only while the part that fades cannot be seen (explore.js's `gal:swap`). The Gallery is as it was. | `verify_socialsearch.py` (12, 13), `verify_social.py` (2), `verify_socialactivity.py` (1), `verify_socialapp.py` (11), `verify_socialsettings.py` (6, 7) |
| Follows at `/social` (`social/follows.py`, `_follow.html`, `follows.js`): B, yours alone. Follow first in the row on somebody's page (before Share and ⋯), the action's purple with the pen's plus, Following once tapped (the quiet button, its check drawing itself; both words in one grid cell, so nothing beside it moves), never on your own page, a blocked person's or a card; a tap on Following asks once ("Unfollow Theo?"), nobody told. Every profile says its counts under the @handle (the map's step 5): "3 followers · 2 following", "New here" while nobody follows them (never a zero), a following count only when it isn't zero; counted by whoever looks, as a like's count is (a block either way or a takedown leaves a person out, a mute changes no number), one read on the follows' own indexes, and after a tap the answer's counts fade in where the old ones faded out. On anybody else's page they are words, and nothing of who follows whom is in the page or its source; on your own each count is a 44px button opening your lists on its own list ("Followed by…" is gone) in Make's sheet, the one pill between them, newest first with when; each row wears their page's Follow button (the owner's "A", Nov 15): Following asks "Unfollow Theo?" over the lists and the row stays with Follow, Follow on a follower you don't follow back, your page's counts changing in place, your own; one person's buttons on a page stay in step, and one sheet rises over another (`social.js`, Esc the top one's). Only somebody signed in and not taken down follows, nobody blocked either way, never themselves, with the token and Origin, 60 an hour; signed out, a sheet that signs in and comes back with nothing pressed. Home's pill, Following \| Everyone (the Gallery's own, its pick kept on the account, `home_feed`): the people you follow and you, their posts (posts only, as all of Home; Skribl's listing keeps its `authors` for any host), newest first, then "You're caught up…" and Fresh from everyone, never running out; following nobody, a kind card and everyone's. In Activity follows are rows grouped since last looked and a day a row under Earlier, never lighting the bell's dot; following again never tells twice (an unfollow keeps the first time, `ended_at`). A block ends a follow both ways for good; an account goes with its follows, in code. | `verify_socialfollow.py`, and `verify_createpost.py` (the listing's `authors`) |
| Settings at `/social` (`you.html`'s Theme row, `you.js`): the Theme row first on Settings, the Pad's own words and order (Theme: System, Dark, Light, System's tip the Pad's) and switch (216 x 52, three 44px choices, one weight), "For Blooby, Pad and Flip" under its name; ONE CHOICE, Skribl's own (`skribl_theme_v1`), which the site reads and sets only through Skribl's theme code: every page of the site includes Skribl's head boot (inline, before the first paint, by the page's own nonce, the one inline script its policy allows) and `lib/theme.js`, the row calls `SkriblTheme.set()`, so the Pad and Flip follow it and their switch sets the site; THE BOOT SAYS DARK OUT LOUD (`data-theme` "light" or "dark", never left off; every theme-color meta carrying both grounds follows), so `social.css` reads light, dark, and nothing stamped (the device), its dark ramp written twice and held to one; a choice cross-fades the page in the site's 0.28s while the pill slides (Reduce Motion: a fade, the pill put there), a tap during it kept, the next page in the choice from its first frame; the gear says Settings on your profile, and a desk's rail has Settings above You, lit on Settings; signed out, nothing new. | `verify_socialsettings.py`, `verify_theme.py` (the boot on a host's page), `verify_social.py` (the policy, the seam) |
| The ☰ at `/social` (`_menu.html`; the map's step 5): on a touch phone at the top left of Home and the Gallery and nowhere else, first in the top, 44px every way, drawn in our pen (three strokes of one length, the owner's "equal lines", Nov 14) in the top's ink, the bell's; a desk has none. It opens the site's own sheet, the ⋯'s, rising from the bottom (read on every frame; under Reduce Motion it fades where it rests), titled with your name: Settings, Community rules, Privacy, Your reports (an admin's alone) and Sign out (a form with the page's token, which the Gallery's page carries signed in), its rows one card, no Help; signed out, titled Blooby: Sign in, Community rules and Privacy. A row picked opens what it says, the sheet going down as it does; it has no Cancel, and Esc, a tap outside, its grip and a swipe down give the ☰ its focus back. | `verify_socialsettings.py` (10) |
| A LIST OF CHOICES ON A SHEET IS ONE CARD (the owner's "B, equal lines", Nov 14: "Do we need everything to be in a pill?"), as the Pad's own menu list draws it (styles.css `.menu-list`): the rows on one rounded 16px card with nothing of their own behind them, touching, and between two that show Apple's thin line (the owner's "Apple's thin line", Nov 14): one screen pixel (`--hair`), from where the row's words start to the row's inside edge, in `--row-line`, no top border. The site's menu sheets (the ☰'s, a post's ⋯ yours and somebody else's, a comment's ⋯, a person's ⋯) on the site's tokens for those roles (`--row-bg`, `--rule`), the risky rows (Report, Block, Delete, Remove) a card of their own 12px under the other, and no Cancel: Esc, a tap outside, the grip and a swipe down close them; Report's reasons one card. Skribl's, the Pad and Flip alike (shared templates): the menu's list, Export's formats (`.export-list`), Your drafts (`.sdrafts-card`) and As a file, Ask's People often ask, each the menu's white card, its lilac edge, its drop and its rule. A key's ring on a row is drawn inside the row, the first and last rows turning with the card's corners, so the card's edge never cuts it. Kept as they were: Report's Cancel \| Send report, Mute's and Block's pairs, Make's two doors, Your face's three ways, Settings' section cards, the Pad menu's four tiles, every pill slider, the Library's ⋯ popover. | `verify_socialposts.py` (16), `verify_socialsettings.py` (10), `verify_contrast.py` (ONE CARD), `verify_menu.py` (the drafts' card) |
| Mutes at `/social` (`social/mutes.py`, `_mute.html`, `mutes.js`): C, quiet everywhere, for you alone. "Mute @theo" in the ⋯ first on their page and after Share… on their posts and drawings (before Report and Block), its line saying what it does and "They aren't told.", a closed eye in our pen, never a speaker; signed in, never on your own, never while a block stands. Nothing asked first: the tap mutes, their cards fold away from Home (a fade, then the room closes), their page's line opens, and a toast says so with Undo for seven seconds (a phone: 12px above the bar; a desk: the foot of the page, the middle of the column), only Undo taking a tap; Undo brings it all back the same way; under Reduce Motion a room is put there only while unseen. What comes to you goes quiet: their posts leave Home (Following and Everyone, in the query), their posts and drawings the Gallery of everyone (Explore, in its own reads), and their drawings Skribl's listings of everybody's (the host's feed filter, told a listing's `author` by Skribl and leaving them out only of a listing of many people's); their comments fold to "Someone you muted said something. Show", hidden for real, Show opening one for the visit; their comments, answers, likes and follows leave Activity and never light the dot. What you go to stays: their page ("You muted Theo · Unmute", to you alone), their posts, their Gallery; the visibility policy is untouched. Counts and "Liked by…" stay true. A mute never touches a follow (rule 3: "You still follow them."). Settings lists Muted above Blocked, nobody hidden listed. Token and Origin, 60 an hour, never yourself, nobody gone or blocked either way; whom you muted is one read a request; an account goes with its mutes both ways, in code. | `verify_socialmute.py`, and `verify_hostseams.py` and `verify_createpost.py` (the feed filter's `author`) |
| Nudges, push notifications at `/social` (`social/push.py`, `push.js`, `push-sw.js`; docs/SOCIAL-SITE.md section 19): A, the dot's rule, what buzzes is what lights the bell's dot (a reply, something said on your post, a mention), likes, follows, reposts and quotes waiting until a device's own switch says otherwise. A nudge is Activity's newest new row of its kind, word for word (`activity.sentence`, `activity.SAYS`, the page's words too), its words in quotes or "Tap to watch it draw.", the row's link, one tag and Topic a row, the number of things lighting the dot; whatever Activity leaves out never buzzes, and a device is never told a row older than the newest it was told. Sent only after the request commits, from two threads of the process's own, reading, then letting go of the database, then talking to the push service; only to Apple's, Google's, Mozilla's or Microsoft's push services over https, never a redirect; 404 or 410 takes the device. Sealed per RFC 8291 (its worked example byte for byte) and signed per RFC 8292 with a key made from `SECRET_KEY` (or `SOCIAL_VAPID_KEY`). A device lives with the sign-in: signing out here, Sign out everywhere and deleting the account take it, in code; another account signed in there lets it go. Activity's card asks once (Not now for good, Turn on from the tap) and glides; Settings' "Notifications on this phone" is a row a kind with Theme's switch, one state drawn at a time (on, Turn on, told no, an iPhone's way to the Home Screen, a browser that cannot); opening Activity clears the number and the nudges shown. Send me a test nudge sends one to this device at once and says what its push service answered, by name and in its own word (20 an hour); a refusal of a real nudge goes to the log. Token and Origin, 600 an hour. | `verify_socialpush.py`, `verify_socialauth.py` (14, the chain) |
| Saved drafts on the server have a per-author byte budget (`SKRIBL_MAX_DRAFT_BYTES`), raster-only thumbnails, and a list that reads no payloads. | `verify_hostseams.py`, `verify_clouddrafts.py` |
| Work on the canvas, including media still on its way back from the store, is asked about before a draft replaces it; a late store answer never lands on a different document; Save draft waits for a file still being read. | `verify_amber.py`, `verify_clouddrafts.py` |
| Every bottom sheet closes on a tap of its grabber or a swipe down, owns the touch from its first pixel (no pull-to-refresh), and eases away. | `verify_sheetswipe.py` |
| Every drawer shows what a tap opens: a tile's choices end on the screen, or the page stops with the top of the drawer at the header; a music door shows all of what it opens, its tile kept below the header and the timeline's copy; it glides there (straight there under Reduce Motion), only ever down, keeping Text's words in view; one tile swapped for a shorter one glides rather than clamps; and every `.dp-tile` in the page is one the check presses. | `verify_drawerreveal.py` |
| Drawers beside the drawing on a desk (`lib/drawers.js` sideApply; the owner's "all yes", Nov 25): with a mouse, where the drawing fits whole beside it, Pen, Photo, Music and Text each open as a 392px column at the drawing's right, its top level with the drawing's; the drawing and what sits under it (the Pad's dock; Flip's page strip and dock) slide left only as far as needed (the drawing 16px clear of the drawer's tab), gliding there and back (one frame under Reduce Motion); the header stays; nothing scrolls; what a tile or a door opens shows by the drawer's own column gliding inside itself (`lib/drawerdetent.js` sideBox, the Music doors' own sum); the eyedropper leaves it out; a press on the drawing that puts a drawer away holds it still under the pen until it lifts, and a stroke lands where it is drawn. ROOM FOR THE DRAWER (the owner's "All yes", Nov 26): a drawing too wide to sit beside a drawer (a 16:9 one fills a desk's width) gets a little smaller as well, the least it needs and never past three quarters of its width, taken out of its row as padding half each side so it stays over its dock, the drawer level with its top, gliding there and back; Flip's page strip runs under the drawer to its right edge and the drawer ends above it (`--side-max`); a pixel's rounding on a decision without a glide is kept as it was. THE DRAWER'S TAB (the owner's "All yes", Nov 26): beside the drawing the drawer wears a tab on its edge facing the drawing, 22px below its top, 24px out, joined to it (its line runs on round the tab, none where they meet), a › mark in the drawer's ink, the drawing 16px clear of it; a button named "Close the drawer", just before the drawer in the keyboard's order, the focus back on the drawer's own button when Enter closes it; it lights up under a mouse and rests with the drawer in a replay. A DRAWER CLOSED BESIDE THE DRAWING SLIDES AWAY, its tab with it, fading as it moves right (inert, its panel hidden at once; gone at once under Reduce Motion). Below as before on a narrow desk (one that would take more than a quarter), a tablet and a phone, with no tab; a resize decides again; the tools tray never beside. | `verify_drawerside.py` |
| The Gallery card's fade takes its colours from the drawing under it: invisible on empty paper, inside the drawing's round corners and off the card beside it; each glass control takes the tone of what is under it; the time reads at 4.5:1 on painted pixels; a drawing that cannot be read keeps the scrim; Mute steps aside on a silent drawing, on the card and in full screen, from the first paint. | `verify_cardfade.py` |
| One full screen, everywhere: the Gallery's and the Library's full screen is the link page's -- its band (the scrubber in the drawing's shape, the artist's clock, the words with every speed, the buttons), its x and the drawing's ground to the screen's edges -- built by `lib/fullbar.js` band() in the link page's markup, from styles.css's own rules (`fullband.css`, emitted by `harness/tools/cssgraph.py` like `player.css`), with who drew it in the top corner. | `verify_onefull.py` (every part measured against the link page's), `verify_seam.py` (`fullband.css` byte for byte what the tool emits) |
| A post's full screen is that one too (the owner's "yes to A and all your picks", Nov 16; `lib/postfull.js`, `postfull.css`, `skribl_full_assets()` and `skribl_inline(full=, full_meta=)`): on the Skribl site a post's line, and a comment's drawing's, ends in a full-screen button after Repeat (32px drawn, 44 to a finger; none on a page that does not load the full screen), which opens the band around the post's own player, the post's words over "Name · @handle" in the corner; the drawing carries on from where it was, playing or paused (one never played is played), the page behind held still; leaving puts the post back as it was, its line given back (`inlineplayer.js` unband(), the band borrowing it afresh the next time), Repeat and the speed picked in full screen with it, and the focus on the button (opening takes it onto the band's Play). The band's rules reach only a band's host and what is inside it (`:where(.skfull-host, .skfull-host *)` in `fullband.css` and `gallerysection.css`), so a post's own line under it is never restyled, and the band steps back while the drawing plays. | `verify_socialposts.py` (18), `verify_seam.py` (the scoped sheets byte for byte), `verify_inline.py` (the embed's ratchet: the full screen is not in it) |
| Every full screen's bar takes its colours from the drawing too (the Gallery's and the Library's, the link page's, Pad's and Flip's), read by the card's own reading (lib/smartfade.js): the fade unseen on empty paper and no fog on a dark drawing; every word at 4.5:1 on its worst painted pixel; each control's glass by what is under it, turning with the theme, the dark glass violet (a 14% white came out grey; No dinge, the last four) and a lit control a stronger violet; full screen's x in the top corner the same glass, toned by what lies under it (`also`); a title crossing a tall drawing's edge in a capsule; a photo under the drawing as a picture of its own keeps the scrim, and the x its own disc. | `verify_fullsmart.py` (glass, photo), `verify_cardfade.py` (the card's violet) |
| On a window with room the canvas shows past the size it was drawn at and its bitmap grows with it, so it stays sharp, pixel for pixel at 1x (the Pad's up to 3x the drawing, Flip's up to 2x, inside its frame); the drawing's own units, its payload and everything that leaves the canvas (files, post card, drafts, thumbnails, the fill) keep the drawing's own size, and a new drawing starts in the shape the 720px column gives it. | `verify_bigcanvas.py` |

**One from v179 did NOT survive, and is recorded here rather than quietly
dropped.** "Segmented controls state a height" was true when written; `flip.css`
now says `--seg-h intentionally NOT set`, because the control has only been
measured on one machine and its height follows the installed font. Opting it in
would mean choosing a number for every viewer. The rule was superseded by a
deliberate decision, and START-HERE asserted the old one until v282.

### What the gates caught, including one I built last release

**`verify_a11y`'s modal census passed over both new dialogs.** The v280 gate
enumerated `[aria-modal="true"]` from the live DOM and primed the one
runtime-built dialog it knew about by name. Two more arrived in `recoverykey.js`
and the census could not see them, because a sweep taken at load cannot see a
node that does not exist yet. That is the hole the v280 note warned about, in
writing, one release before walking into it. There is now a **JS-source
census** beside the template one: every non-minified `.js` under
`skribl/static/` that mentions `aria-modal` has its assigned element ids
extracted and required to be recipe-backed, so the next runtime-built dialog
fails the suite instead of slipping through.

**The wrong-key test passed with the bug fully restored.** Deleting a row calls
`confirm()`, Playwright dismisses dialogs by default, so `destroy()` never ran
and the assertion was checking that nothing had changed after nothing had
happened. It drives `destroy()` directly now. Measuring something ADJACENT to
the claim is the recurring failure of this whole sequence of releases — it has
happened in most of them, to me, in assertions I had just written — and it is
the argument for mutating every new assertion rather than trusting a green
one.

### `verify_a11y.py` generates its population now

Three of seven `aria-modal` surfaces were routed through `SkriblModal`; the
suite tested one of the three by hand and passed. The audit named the shape:
*a global semantic claim should generate its test population from the DOM, not
from a manually chosen specimen.* The suite had already learned to assert
behaviour instead of attributes, and then asserted the right thing about the
wrong population — the same error one level up.

Every surface routes through the utility — eight when this was written, the
eighth the recovery panel; the gallery's report sheet and the profile's key
dialogs have joined since, and the census counts them rather than this
sentence. Section 2 reads `[aria-modal="true"]` out of the live DOM; a surface
with no recipe **fails** rather than being skipped, a recipe naming a deleted
surface fails too, and a template census backstops the dialog that lives behind
an unrendered branch. A dialog built at runtime escapes a census taken at load,
so `recoverykey.js`'s overlay is primed before the sweep — anything added the
same way must be primed too, and the template census is what will say so.

**It immediately found a defect in `modalfocus.js` itself.** `close()` checked
`isConnected`, but an opener can be present and `display:none` — the leave
confirm closes the menu holding its opener on the way up. `focus()` was then a
silent no-op and the user landed on `<body>`: the exact outcome the utility
exists to prevent, reached through the one door it did not cover. It checks
`offsetParent` now and falls back to whatever had focus when the dialog opened.

### Two gates that were representatives of a global contract

`verify_txcontract.py` scanned two files — the two where the v224 violation
happened to be found — so `takedown.py` could have committed the shared session
from request-shaped code and stayed green. It scans every module now, by AST
rather than by grep, with exemptions named **per function**. Per function
because widening it produced a finding at once: `storage.py` is a library a
host imports and only its batch function may commit, so a file-level allowlist
would have waved the whole module through. Its stale-exemption check then
caught an exemption I had granted on an assumption, for a function that does
not commit at all.

`verify_docs.py` gates the CI-cost claim. Two of this release's findings were
stale statements in **source comments**, where the v279 sweep never looked: 22
lines above the delete routes still calling the v278 identity gate "the whole
design", and the header of `harness.yml`, which used to say a heavy CI day had
burned a monthly Actions allowance. This repository is public and every job
runs on `ubuntu-latest`, so there is no allowance — see `WORKING-AGREEMENTS.md`. The gate
asserts the half that is checkable offline: while every runner is standard,
nothing current may call this project's minutes finite or billed. Move to a
larger runner and the claim becomes sayable again and the gate stands down by
itself.

### `verify_a11y.py` — keyboard and assistive technology, as its own suite

Added after an accessibility audit of v278, and a suite rather than more of
`verify_ux.py` because of the audit's structural point: the tree carried
thousands of assertions — the count is in `harness/RELEASE.md`, never typed
here — while basic keyboard failures were visible in the source. Three
playback scrubbers were pointer-only, two of them declaring `role="slider"`
with no tabindex, no `aria-valuenow` and no key handler — announcing a control
that could not be operated. Every `aria-modal` dialog did nothing about
focus — this said "Five" until v280, when counting them for the enumeration
gate found seven.
Visible slider captions were not labels. Segmented controls kept selection in a
CSS class. Nothing announced that a post had succeeded or failed.

Its own rule: **assert the behaviour, not the attribute** — `role="slider"`
being present is exactly what was true while it was broken. It presses keys and
reads what moved, focuses things and reads where focus went.

Two things it caught that the audit had not: five unnamed controls in Flip's
share sheet and image drawer, and `--text-faint-2` on `.accordion-count` at
3.47:1.

And one about ITSELF. The contrast gate's first version exempted any line
matching `--text-`, meaning to skip the token definitions — but
`var(--text-dim)` contains `--text-`, so it skipped every use as well and the
check was vacuous. Putting a failing token back on readable text left it at
37/37. Definitions are excluded by shape now.

### Identities are opaque text

`skribl_posts.user_id` is `String(255)` behind a `TypeDecorator`, not `Integer`.
The column was Integer while `docs/INTEGRATION.md` advertised "your user id",
so a host using UUIDs, ULIDs or an OAuth subject could not integrate at all.
Integer hosts are unaffected — 42 stores as "42" and both sides of every
comparison normalise. `author.id` in the API is a JSON string now.

**Both sides, not just the argument.** Normalising only the incoming id passed
every suite that goes through `create_post` and failed `verify_privacy`, which
builds `SkriblPost(user_id=7)` in memory and never flushes it — so the
TypeDecorator never ran and an author could not read their own private post.
The type covers what is stored and loaded; the comparison covers what was never
persisted. Both are needed and for different reasons.

### The MP4 attestation — what a seal can honestly say about H.264

`verify_mp4.py` skips wherever the browser has no H.264 encoder. Until Oct 30
that was every Chromium the harness drove: Playwright shipped the open-source
build, which had WebCodecs but no H.264 encoder. Build 1243 (Chrome 153,
Playwright 1.63) has one, so the suite now runs in this container and in CI's
shards, and the seal reports it with the rest; the attestation below is then
evidence from real Chrome beside the local run, rather than the only evidence.
(Probing `VideoEncoder` on `about:blank` reports "no WebCodecs at all" and is
misleading — the suite checks on a real page, where the API is present and
asks each `avc1.*` profile in turn.)

The `mp4 (real Chrome)` CI job covers it, and until v279 its result never
reached the archive: the seal said `skipped 1 (verify_mp4.py)` and nothing
about whether the gap had been closed elsewhere, so a reader could not tell
"not covered" from "covered somewhere you cannot see". An audit of v278 called
that an evidence gap rather than a defect, which is exactly what it was.

`harness/MP4-ATTESTATION.txt` is that job's answer, and `RELEASE.md` now
carries an `mp4 (H.264)` line computed from it. **The tree hash in the
attestation must match the one the release froze** — evidence about different
code is worse than no evidence, because the seal would then assert coverage it
does not have. Three outcomes, all stated rather than implied: verified, STALE,
or NOT VERIFIED with the command to fix it.

It never blocks a release. Whether an unverified MP4 path is shippable is a
product decision; the seal's job is to state the fact.

The file is excluded from BOTH tree-hash lists (`release_run.GENERATED` and
`run_harness.sh`'s `_tree_files`) for the same reason `RELEASE.md` is: it names
a hash, so including it would make writing the evidence change the thing the
evidence is about. The two lists must stay identical — that is the v221 defect.

The job also keeps the files it checked (after v325, for an auditor who asked
for the exports themselves). With `SKRIBL_KEEP_EXPORTS` naming a directory,
`verify_mp4.py` writes each export it inspects there; unset, it writes nothing.
The job reads them back with ffprobe (streams, codecs, decoded frame count,
whether the audio is louder than silence, a contact sheet of each Flip) into
the `mp4-exports` artifact, beside each file's SHA-256 and the tree hash (a
manual run also prints the files into its log, for a reader the artifact
store refuses). That
directory is outside the checkout on purpose: `tree_files` walks the disk, so a
file kept inside would change the hash the attestation names.

### Environment traps, in the order they will bite

* `apt-get update` fails outright until the blocked nodesource repo is moved
  aside: `mv /etc/apt/sources.list.d/nodesource.list /tmp/`. Then install
  postgresql, start it, create the `skribl` role and database.
* `pip install -r constraints.txt --require-hashes --break-system-packages`,
  then the harness's own (`pip install -r harness/requirements.txt`: playwright,
  Pillow, Flask-WTF — none of them in the app's runtime), and
  `python3 -m playwright install chromium`.
* **PILLOW IS NOT IN requirements.txt AND THREE SUITES NEED IT.** `verify_cssplit`
  and `verify_smudgeblur` CRASH without it; `verify_sizeclass` is worse — it
  reports 81/82 with a single tidy failure while **eight of its assertions
  silently do not run**, which is the shape of problem this whole harness exists
  to refuse. With Pillow it is 89/89. A v273 release run reached batch 42 of 44
  before these three sank it. `pip install Pillow`.
* **PLAYWRIGHT MUST MATCH THE CHROMIUM BUILD ON DISK.** Check with
  `ls /opt/pw-browsers` (or wherever `PLAYWRIGHT_BROWSERS_PATH` points): build
  1243 wants playwright 1.63, and 1.56 fails to launch with an executable-not-
  found error that reads like a missing browser rather than a version mismatch.
* **THE INTERPRETER MUST BE THE PINNED 3.12, and a container's default may not
  be.** `verify_docs.py` fails the run outright when `.python-version` and the
  running interpreter disagree — deliberately, because evidence produced on a
  different interpreter from the deployed one describes nothing. If the default
  `python3` is not 3.12, build a venv from the 3.12 that is installed and put it
  on PATH ahead of everything for the whole run.
* **THE SEAL AND CI DO NOT TEST THE SAME THING, and CI's mode is the stricter
  one.** `release_run.py` runs its batches SEPARATELY, each getting a fresh
  server and database on a quiet machine. CI runs every suite in ONE invocation
  on a contended two-core runner. (Both counts were typed here once and both
  went stale — the suite count was caught by `verify_docs`, the batch count was
  not, because nothing checks it. `release_run.py --dry-run` prints them.) Anything sensitive to write contention or to
  cross-suite state therefore passes the seal and fails CI — which is exactly
  what happened: a 500 under SQLite lock contention (v274) failed main's sqlite
  job on one push and passed it on the next, with the bug unchanged in both,
  while v273 sealed green TWICE on this box. **A green seal is not a prediction
  that CI will be green — and a CI failure that clears itself on the next push
  is not thereby a flake.** If a suite fails only in CI, do not
  reach for "flake": reproduce it by loading the machine —
  `for i in $(seq 1 12); do (while :; do :; done) & done` — and it will very
  likely fall over locally too.
* **A suite's subprocess servers send stderr to DEVNULL, so the traceback you
  need is thrown away.** `verify_review.py`'s `server()` helper does this. When
  a request 500s inside a suite-launched server, patch that redirect to a file
  before theorising — the v274 bug named its own cause in the first traceback
  captured, after the wrong writer had been suspected on reasoning alone.
* **PostgreSQL: `verify_postgres` SKIPPING locally is the designed
  configuration, not a weaker seal.** The `postgres` CI job runs it on the tree
  being sealed and writes `harness/POSTGRES-ATTESTATION.txt`, which the seal
  checks against the frozen hash. Do NOT start a cluster here during a seal:
  `WORKING-AGREEMENTS.md` carries the measurement of what it does to the timing suites. For
  debugging outside a seal the suite wants
  `postgresql://skribl:skribl@127.0.0.1:5432/skribl` (override with
  `SKRIBL_PG_DSN`), and PostgreSQL dies between tool invocations, so start it
  in the same invocation as whatever needs it and check `pg_isready`. This entry
  used to tell a sealing session to start the cluster and expect a fixed count,
  and both halves had gone stale.
* **Background processes do not survive between invocations**, and one
  foreground invocation is capped well below the length of a full aggregate
  (`WORKING-AGREEMENTS.md` gives the current figure). `setsid`, `nohup` and `disown` do not
  help: the v312 release run was reaped that way at batch 3/55 with no error.
  Run it through the agent's own tracked background runner, or in `--budget`
  slices. Either way `release_run.py` checkpoints, re-verifies the frozen tree
  hash on every resume and aborts if the tree changed. **Resume WITHOUT
  `--restart`**, because `--restart` discards the checkpoint. The checkpoint is
  deleted on completion.

### Eight suites could fail silently — fixed at this seal

`run_harness.sh` takes ok/FAIL from a suite's **exit code**. Eight suites
(`verify_amber`, `verify_audio`, `verify_dots`, `verify_feed`, `verify_fix`,
`verify_lib`, `verify_privacy`, `verify_seam`) printed their failures and then
exited 0. The runner reported them as `ok`, and a full aggregate would have been
recorded as PASS with a failed assertion inside it. `verify_docs` was the ninth,
caught in the act: it printed `32/33 passed FAILURES: ...` and the runner said
`ok`.

All nine now end with `sys.exit(1 if bad else 0)`.

**This is very likely what the `verify_amber` "flake" earlier in the session
was.** It was reported as a crash by a parser bug that has since been fixed, and
it would ALSO have been reported as ok had it merely failed. Two independent
reporting holes over the same suite. Do not trust any green run recorded before
this seal for those eight suites.

The lesson generalises: **a suite's failure has to travel through the channel the
runner actually reads.** Printing it is not reporting it.

### The next step, and the honest distance

**THE JS TARGET IS MET. This section argued for years that it could not be, and
that argument is over.** `verify_jsstrip.py` asserts the player reaches the
153,600 B target after the serve-time strip, with room to spare, and
`verify_player_isolation.py` holds the ratchet below it. Run either for the
number; it is not typed here, because every previous number in this section
outlived the tree it described by dozens of releases.

How it was won, and why the old plan was the wrong plan:

* **Self-contained IIFEs** — `editor_export`, `editor_post`, `editor_menu`.
* **Wiring extraction** (move STATEMENTS, leave functions and state) — both
  drawers: `editor_music`, `editor_photo`.
* **The carves — every `skribl/static/editor_*.js`.** This list was once
  four names, then nine, and was stale both times, so it is the glob now. Each
  is absent from the player. Pad loads every one, `editor_compose` only in a
  host's composer, `editor_face` only in its face mode, `editor_letters` only on Your hand
  (`/skribl-pad?letters=1`) and `editor_text` everywhere but there; Flip loads
  `editor_compose`, and only in a host's composer (its side of Text is in
  `flip.js`); the player loads none. `verify_player_isolation.py`
  reads that list OFF DISK rather than from a hardcoded tuple, which is how a
  new carve is covered the day it lands.
* **The serve-time comment strip** — `skribl/jsstrip.py` removes comments from
  the RESPONSE; the files on disk keep every word. This is what closed the gap,
  and it moved no source at all.

**The plan this section used to prescribe was function relocation, and it was
never executed.** It held that shared paths NAME the editor-only functions, so
moving them means dependency inversion rather than relocation — and that even
moving all of them still would not reach the target. Both statements were true
of the tree they were measured on. Neither is now the binding question, because
the strip got there without moving a function. The AST tool built to de-risk
that relocation (`harness/tools/refgraph.js`) was DISPROVED — it fails its own
superset gate and would move the four functions the v132 attempt got wrong. The
v132 failure was load order, not classification. Read `docs/REFACTOR-v132.md`
before planning anything here.

**THE PLAYER'S CSS IS UNDER ITS TARGET SINCE v315 (SK312-004; owner: "yes").**
`player.css` was about 63% comments, served to every visitor of a shared link.
CSS is now comment-stripped on the way out exactly as JavaScript is
(`skribl/jsstrip.py`, busted URLs only, fallback to the raw bytes), and
`verify_player_isolation.py`'s `CSS_RATCHET` is tightened to the served size.
`verify_jsstrip.py` proves the strip changes nothing by comparing every
element's full computed style, stripped against raw, on Pad, Flip, Gallery and
a real `/s/<id>` player. Further cuts are `harness/tools/cssgraph.py`'s
classifier, not a carve.

**The rule that governs all of it:** a binding declared in an editor-only file
does not exist on the player, so any player code touching it throws. Wiring moves
because nothing names it; state and shared functions cannot. Ask which direction
the reference runs.

### Before touching the loop engine

The isolation fixture carries real audio and asserts playback through an analyser
tap. Keep it that way. A silent fixture made Chrome's coverage profile report
every loop-building function as unused, and acting on that would have shipped a
player that cannot play music — with the suite calling it green.

---

**Read this file, `DECISIONS.md` and `ARCHIVE-README.md` before changing
anything.** The per-version narrative lives in `DECISIONS.md` and in git history
(`docs/HANDOFF.md` is the v100–v131 archive). Everything below was verified by running it, not by reading the code.
(Historical sections below narrate older work; the numbers in prose are that
era's, not this build's.)

---

## What this is

Skribl is a browser drawing/animation tool — **Pad** (records a drawing and
replays it with its timing), **Flip** (frame-by-frame animation) and a
read-only **Player** — packaged as a Flask blueprint to drop into a social
platform.

Beside it, `social/` is the start of that platform, the Skribl site
(docs/SOCIAL-SITE.md): a host of Skribl through the same public seams any
host uses, plugged into the demo's own app at `/social` so it shares the
demo's Skribl. Phase 1's first piece is its frame: Home, Explore and Make;
its second is sign-in, invite-only, with passkeys, in tables of its own
(section 9 of that document). Skribl never imports it. Its map, since
Nov 13, is section 16 of that document: a post is the one thing people
share (words, and a drawing or a Flip), Home is posts, Explore is the
Gallery of everyone's drawings, and a profile is Posts · Gallery · Likes ·
Bookmarks · Drafts; part two of it (section 17: the composer, bookmarks,
reposts and quote posts, and what comes next) since Nov 14. Section 18 is
the comment thread, the owner's yes of Nov 17, step 1 built: bubbles, the
post's choices on every comment, every list one level of direct replies,
each opening its own page. Read it before changing what the site shows.

    SKRIBL_VERSION   see skribl/core.py — the archive name derives from it.
                     This line used to hand-type it, and read v191 while the
                     code said v211: four releases stale, in the file whose
                     whole opening section is about numbers going stale
                     silently. Read the constant.
    client assets    app.js / flip.js / styles.css / flip.css and lib/ — one
                     continuous line of work; the per-version story is in
                     DECISIONS.md and git history
    harness          see harness/RELEASE.md — the count is generated, and a
                     hand-typed one is exactly what drifts
    migrations       skribl/migrations/versions — count the files; this line
                     said "6" for a dozen releases while the directory grew
    last run         see the stamped stanza below — it is generated, and a
                     hand-typed total is exactly what drifts
    tree hash        see the generated stanza below — NEVER typed here
                     (a hand-typed hash in this file is what made an
                     external reviewer distrust the whole archive)

**Release evidence lives in `harness/RELEASE.md`** — every suite on disk,
on one frozen tree, generated by `harness/release_run.py`. The stanza below is
narrower: it records only the LAST `run_harness.sh` invocation, which is a batch,
not the release. When the two disagree it is because they answer different
questions; RELEASE.md is the one to quote.

**The last recorded run** — generated by `stamp_docs.py`, never typed:

<!-- HARNESS-COUNTS -->
**PASS WITH SKIPS — 14734 assertions across 174 reporting suites (175 on disk, 1 skipped), none failing** on sqlite as of v330 (tree `cdb7d50996ab`).

These totals are generated by `harness/stamp_docs.py` from `harness/LAST-RUN.txt` — never typed. `verify_docs.py` fails if any doc disagrees with the recorded run.

Skipped in that run: verify_postgres.py. A skipped suite contributes zero assertions and is not evidence of coverage.
<!-- /HARNESS-COUNTS -->

**The deployed runtime is pinned to Python 3.12** (`.python-version`, mirrored
by `PYTHON_VERSION` on the Render service). `constraints.txt` is a hash-locked
cp312 environment and the recorded evidence is produced on the same interpreter,
so the numbers in `harness/RELEASE.md` describe what production runs rather than
a configuration nobody has. Render's default Python depends on when the service
was created and moves over time; unpinned, the build resolves `requirements.txt`
fresh and runs versions no assertion ever exercised. `verify_docs.py` fails if
the pin, the lock and the interpreter running the harness disagree.

**Verify the archive first, in one command:**

    cd skribl-v*
    grep -Ec '^[0-9a-f]{64} ' SHA256SUMS            # N: the manifest's own entry count
    sha256sum -c SHA256SUMS | grep -c ': OK'        # must equal N

    # v224: the expected count is no longer TYPED here at all. It used to be,
    # with a note explaining that you should compare against the manifest
    # rather than against the number — which is an odd thing to write beside a
    # number, and it went stale anyway every time the file set changed. The
    # manifest already states its own size; asking it is strictly better than
    # asserting it. `verify_docs.py` still checks any count that IS typed
    # elsewhere against SHA256SUMS.

---

## The live demo

`skribl-live-demo.onrender.com` — a Render Starter web service ($7/mo) deployed
from GitHub (`MrBlood/skribl-live-demo`, branch `main`), backed by a paid
Postgres Basic instance ($6/mo), running the `inline` media backend. It runs
WITHOUT the demo identity: its environment holds `DATABASE_URL`,
`MAX_CONTENT_LENGTH`, `SECRET_KEY`, `SKRIBL_TRUSTED_PROXIES` and
`WEB_CONCURRENCY` and no `SKRIBL_DEMO_*` (read with the owner on Render, Nov 3,
names only), so `/demo-login` is not there and there is no sign-in key to rotate.
Since Nov 10 it also holds `SKRIBL_CSRF_PROTECT` (1: the site at /social signs
people in, and the Pad posts as them only with it on; read off the live Pad's
token after the owner's deploy) and `SKRIBL_SOCIAL_FIRST_INVITE` (spent: the
owner joined as the site's first person and admin that evening, and may delete
it). `SKRIBL_TRUSTED_PROXIES` is 1 (the owner's screenshot, Nov 10).

**The site's demo people** (Rook, Pip, Mira, Juno and Theo on /social) were
made through the site as people use it, by `harness/tools/demo_people.py`
(its section in `harness/tools/README.md`): faces and drawings drawn with
real pen input in the site's own Pad and Flip, so every tile shows its
picture. Their passkeys lived in that session's scratch folder and went with
it; to act as them again, ask the owner for a sign-in link each (Settings,
Invites and sign-in links).

**The deployed code can lag this tree** — Render deploys from `main`, so
anything merged is live after its build finishes and anything unmerged is not.
Check the version label, the last line of the editors' ⋯ menu, before
diagnosing anything.

**Two operational facts learned the hard way:**

* A free Postgres instance expired mid-session and every `POST /api/skribls`
  returned 500 with `failed to resolve host 'dpg-...'`. It looked exactly like
  a broken client, and three client-side theories were chased before a server
  log settled it in one line. **Check the server log first.**
* **HISTORICAL — this is the incident that caused the pin, not the current
  state.** Render was building on **Python 3.14** while `constraints.txt`
  carried cp312 hashes, so production resolved `requirements.txt` fresh and was
  NOT running the versions the harness tested. **Fixed by pinning:**
  `.python-version` holds 3.12 and `PYTHON_VERSION` mirrors it on the Render
  service — see "The deployed runtime is pinned to Python 3.12" above, which is
  the current statement. `verify_docs.py` fails if the pin, the lock and the
  interpreter running the harness ever disagree again.

  Two statements about the runtime appeared in this file at once, one current
  and one historical, with nothing marking which was which. An external review
  flagged it: *"Both statements cannot describe the same current deployment."*
  It was right, and the fix is the label rather than a change of fact — CURRENT
  STATE and PAST INCIDENTS must be distinguishable at a glance.

---

## Decisions that are the owner's, not Cal's

**The migration chain collapse is CLOSED.** It required that no database had
run v135-v141. The live Postgres has run at least through `f0a3d81b47e2`. Do not
propose collapsing it again.

**The deploy now runs `alembic upgrade head` — via the RENDER START COMMAND,
not the Procfile (v270).** v267 wired the migrate-then-serve command into the
Procfile and declared the drift closed; **Render does not read Procfiles**
(that is a Heroku convention), so migrations still never ran on deploy, which
the v269 outage proved when the db rate limiter met a `skribl_rate_events`
table the stamp had promised and nobody had built (DECISIONS v270). The
authoritative setting is the Render dashboard's **Start Command**:
`python -m alembic upgrade head && gunicorn app:app`. The Procfile carries the
same line for Heroku-convention hosts and local reference, but changing it does
NOT change the deploy. `skribl/migrations/env.py` also runs a pre-flight that
recreates a baseline table a stamped-over database is missing, so the chain can
run at all on a database whose stamp lied.

**THE PAD/FLIP GUARD ASKS ONLY WHEN WORK IS ACTUALLY AT RISK.** Pad's guard
flushes its draft and asks before leaving for Flip only if that flush did not
leave the draft durable — photo and audio bytes live in IndexedDB
(`lib/draftstore.js`) beside the strokes now, so with working storage it never
fires. In a host's composer, where the Pad keeps no draft, it asks whenever
there is a drawing. Flip, on the way back, applies the same rule to its own
draft: it persists its pages, music and background image, and asks only when
the media did not land durably, or, composing, whenever there is work not yet
added to the post. The predicate's history — content, then
media present, then durability — is written out above `atRisk` in
`editor_draft.js`, and the reason for all three is one: a confirm that is
usually wrong is one people learn to dismiss unread, and then it fails on the
occasion that mattered.

**360px IS THE DESIGN TARGET; 320px IS THE SAFETY NET.** 360 must work properly
on one row — it is a very common Android width, so a two-row bar there is not a
rare fallback. 320 is Display Zoom on a modern iPhone, an accessibility setting
rather than a legacy device, so it must degrade rather than break. The two
surfaces degrade the SAME way since v315: when the row does not fit, both
toolbars become one scrolling row whose far edge fades (`lib/toolscroll.js`,
`.tb-scroll` in styles.css), the owner's pick over a second row.
`verify_layout.py` asserts that every control stays REACHABLE, not that a
particular mechanism is used — an earlier version asserted no-overflow and would
have failed Flip's scroll row as though a deliberate decision were a defect.

**EVERY REPAINT MUST GO THROUGH `makeStrokeCompositor`.** A see-through stroke
painted segment by segment stacks its own overlaps at every captured point —
measured, one 22%-alpha stroke: alpha spread 153 painted directly against 50
composited once. `selRepaint` was the last repaint in the editor passing the raw
`drawDot`/`drawLine` painters straight to `replayTimelineToCanvas`, and
`setTool()` calls it on EVERY tool change, so simply picking the eraser re-beaded
the whole canvas. Preview, playback and all three export paths already routed
through the compositor. If you add a repaint, route it through the compositor or
branch on `strokeLayersOn()` — never neither.

**THE CANVAS LOCK AFTER A TAKE IS DELIBERATE — do not "fix" it.** When a take
ends, `updateCanvasLockCue()` sets `cursor: not-allowed` and the canvas is not
drawable until you tap + Keep drawing or start a New Skribl. This looks like a dead end and is not:
it is the multi-take model, and `endRecordingTake()` says so in a toast —
*"Saved. Play to watch it, or Keep drawing to add more"* — and the way
forward is a "+ Keep drawing" pill floating on the locked canvas (it said
"+ Add take" until the posting mock's plain words); since v288 the
header's Record button is not even there on a finished take (it is a Stop
button while a take runs, and appears idle only over unrecorded ink).
An external design pass in v215 read the lock as a bug and came close to
recommending its removal, which would have turned every stray tap after a take
into recorded timing. The round-trip through Record is the cost of knowing when
the clock is running. If it is ever revisited, the narrower change is to let
drawing on a locked canvas START the next take — same model, no round-trip —
rather than removing the lock.

**Visibility defaults to `unlisted`,** and the migration backfilled every
existing post as `unlisted`. The platform must send `"visibility": "public"`
explicitly or posts appear in no feed, silently. Leave the backfill alone.

**v140's recall framing is confirmed correct** — no database ran the v140 copy
of `f0a3d81b47e2` at `BATCH = 500`.

**The CSS ratchet question is closed:** since v315 `CSS_RATCHET` is set at the
player's served CSS size — see *THE PLAYER'S CSS IS UNDER ITS TARGET* above.

---

## The shared modules, all of them

`skribl/static/lib/` is where a rule lives once instead of twice. The two
editors are separate controllers — app.js and flip.js — so anything they both
obey drifts unless something owns it, and `verify_parity.py` exists because it
did. Eight of these had never been named in any document, which is how a
module gets forgotten and reimplemented.

Surfaces are read from the template `<script>` tags; the descriptions are each
file's own opening line. `verify_docs.py` fails if a lib here is named nowhere.

ONE ENTRY READS "HOST" RATHER THAN A SURFACE. `composehost.js` is the pad
button's lifecycle for a host's own composer, so nothing Skribl serves loads it
except the `/feed` preview standing in for a host. It is in `lib/` for the same
reason everything else is — the alternative is every host writing the same four
rules, three of them right — but it is the one module whose reader is somebody
else's page. It is not in `skribl_inline_assets()` and carries its own byte
ratchet in `verify_inline.py`, separate from the embed's: a page that only
DISPLAYS Skribls never composes one and must not be charged for it.

"host gallery" is Skribl's own Gallery section on a host's page (after v330,
the owner's B): `skribl_gallery_assets()` in
`templates/skribl/_skribl_gallery_section.html`, which loads /gallery's own
modules without its page's (the ••• menu, the theme switch, Report a problem),
beside the player's and `skribl/static/gallerysection.css`. `verify_surfaces.py`
holds that list to /gallery's, in /gallery's order.

"in-post" is the fourth surface: the player a host embeds in a feed post (`skribl/static/inlineplayer.js`, `templates/skribl/_skribl_inline_player.html`).
It loads FOUR of these — `canvassizes.js` for a legacy payload's default
shape, `holdtiming.js` for how long a page lasts and how much of one that
draws itself has been revealed, `audiosession.js`
for the iOS ringer fix, and `photofit.js` for where a background photo lands —
and its own code reads all four. The count has now been wrong twice in the same
way: it said "exactly two ... and reads nothing else from `lib/`" until v281,
when `audiosession.js` arrived with the ringer fix and the sentence did not
move, and it said THREE until v306, when `photofit.js` arrived with the
authored-fit fix and the sentence did not move again. A hand-typed count of a
list the template owns goes stale silently; `verify_inline.py` is what actually
pins the set, asserting both that the macro loads each module and that
`inlineplayer.js` reads it.

`sharecard.js` USED to be a fifth, and v281 dropped it. The idle poster's crop
is literals in `inlineplayer.css`; nothing in the page ever read
`window.SkriblShareCard`. The only reader was `verify_inline.py`, evaluating
`band()` in the page to check those literals still agree with the module's
arithmetic — a real assertion that did not need the payload. The suite injects
the module now (by `evaluate()`, since the page's CSP correctly refuses an
injected `<script>`), and the embed ratchet came down 32,000 → 31,000 rather
than banking the saving as slack.

**The saving is 993 B, not the 5,210 B this paragraph first claimed.** That was
the size on disk; `jsstrip.py` serves these files without comments and the
budget counts served bytes. The correct figure was in `verify_inline.py`'s own
note the whole time. A five-fold overstatement in the direction that made the
finding look better is exactly the kind worth writing down. `verify_inline.py` asserts both that it reads them and that the
macro loads them, because reading a global nothing loads is a silent fallback
rather than a shared rule.

<!-- GEN:MODULE-INDEX -->
| module | loaded on | what it owns |
|---|---|---|
| `artwork.js` | Pad+Flip | The artwork stage — ONE implementation, shared by Pad and Flip. |
| `ask.js` | Pad+Flip | Ask: How it works as one question in your own words (owner, after v323: the Ask mock, "All yes"; piece two of the help in four layers, FUTURE.md 6p). |
| `audioloop.js` | Pad+Flip+player | Skribl shared audio-loop DSP — canonical copy (INTEGRATION step 3b). |
| `audiosession.js` | Pad+Flip+player+library+in-post | Making Web Audio audible on an iPhone whose ringer switch is off. |
| `autosavepill.js` | Pad+Flip | lib/autosavepill.js — the autosave pill: one owner for its five states and, when media is missing, the way out. |
| `book.js` | Pad+Flip | The little book: what Ask's "New here?" opens (owner, after v323: the little book mock, "Yes to all as long as it's kind"; piece three of the help in four layers, FUTURE.md 6p). |
| `brushes.js` | Pad+Flip | Brushes — presets expressed entirely through per-point size and colour. |
| `brushfield.js` | Flip | The arithmetic behind tools that act on ink already on the page. |
| `canvasground.js` | Pad+Flip | The ground a new drawing starts on: Paper in the light theme, the dark canvas in the dark one. |
| `canvassizes.js` | Pad+Flip+library+in-post | Canvas presets — the one table both editors read. |
| `canvaszoom.js` | Pad+Flip | The canvas magnifier: zoom, pan, the HUD, its grip, wheel and Space-drag. |
| `capmore.js` | Pad+Flip+player+gallery+host gallery | A CAPTION AT TWO LINES, AND A "MORE" WHERE THERE IS MORE. |
| `chromefade.js` | Pad+Flip+player+library+gallery+in-post+host gallery | Controls that step back while a drawing plays, and come back the moment someone reaches for them. |
| `chromefit.js` | Pad+Flip | The editors' fit when the chrome around the canvas changes size and the window says nothing -- Pad's and Flip's, one watch -- the canvas's row reaching past the column on a wide window (span()), and the shape the canvas starts in (a new drawing's, startShape; a draft's own, noted beside it). |
| `colorselect.js` | Pad+Flip | Colour selection — the part both editors must agree on. |
| `composehost.js` | HOST | The pad button's lifecycle, for a HOST's composer. |
| `constrain.js` | Pad+Flip | Shift-to-constrain — snap a stroke to the nearest axis, shared by both editors. |
| `draftstore.js` | Pad+Flip+library | Draft media persistence — the bytes localStorage cannot hold. |
| `dragtrack.js` | Pad+Flip | A horizontal drag on a track: the plumbing, once, for both editors. |
| `drawalong.js` | Pad+Flip | Draw along: a drawing from the little book, laid faintly on your own canvas one stroke at a time, for you to trace at your pace (owner, after v323: the little book mock, "Yes to all as long as it's kind"; FUTURE.md 6p). |
| `drawback.js` | Pad+Flip | Draw back: somebody's drawing faint under your pen, so you draw with them, never over them (the owner's "All yes", Nov 19, to the Draw back mock; DECISIONS.md, "Draw back, mocked"). |
| `drawerdetent.js` | Pad+Flip | The draw drawer's HALF detent — one implementation, both editors. |
| `drawers.js` | Pad+Flip | Exclusive drawer controller — the ONE implementation of a machine both editors had hand-rolled: named panels above/below a toolbar, at most one open, the opener button reflecting state, and a scroll that reveals the opened panel without stranding it under browser chrome. |
| `drawfull.js` | Pad+Flip | Draw in full screen, on a desk: the page itself goes full screen, the header and the dock with it, and the canvas takes the room. |
| `drawtiles.js` | Pad+Flip | The draw drawer's four tiles -- Brush, Size, Feel, Eraser -- one implementation, both editors. |
| `editorswitch.js` | Pad+Flip | The menu's Pad | Flip switch moves before it goes (owner's iPhone, after v323: "when I click flip, starts loading flip and never shows the button move, then boom you're in flip. |
| `erasersize.js` | Pad+Flip | Eraser size — shared by both editors. |
| `eventpoint.js` | Pad+Flip+player | Which contact a gesture belongs to — shared by Pad, Flip and the player. |
| `eyedropper.js` | Pad+Flip | Eyedropper — the armed-state machine, shared by both editors. |
| `face.js` | face | The face player: somebody's drawn face, still, or drawing itself once. |
| `faceframe.js` | face | A face from a drawing you already have, placed in the circle and made a face of its own. |
| `floodfill.js` | Flip | Flood fill, expressed in the only vocabulary this project has: strokes. |
| `framebitmap.js` | Flip+player | Frame bitmaps — a painted page is rasterised once per playback, shared rule. |
| `fullbar.js` | library+gallery+in-post+host gallery | The full-screen bar: one transport, and the SAME one on both surfaces. |
| `gridoverlay.js` | Pad+Flip | Grid overlay — the alignment guides both editors draw over the canvas. |
| `handover.js` | Pad+Flip | YOUR HAND, OVER THE EDITOR: for the Pad or Flip inside a host's post (compose mode). |
| `handwords.js` | Pad+Flip | YOUR HAND'S WORDS on an empty canvas (the owner's pick after the "Empty canvas ideas" mock): "Draw anything" on the Pad and "Draw page 1" on Flip, in the owner's own hand. |
| `headerglass.js` | Pad+Flip | The header's ground, only while the drawing is under it. |
| `hello.js` | Pad+Flip | Skribl says hi: the first time Skribl opens, on any screen (FUTURE.md 6m). |
| `helplearn.js` | Pad+Flip | How it works, shown: the Watch tab of the help panel, and its two tabs. |
| `helpsearch.js` | Pad+Flip | Help drawer search + live section counts. |
| `hints.js` | Pad+Flip | First-use hints — one short toast the first time a control is used. |
| `holdtiming.js` | Pad+Flip+player+library+in-post | Per-page timing — the ONE definition of how long a page lasts and how much of a drawing page has been revealed, shared by the Flip editor and every surface that plays one. |
| `homescreen.js` | Pad+Flip | Getting Skribl onto the Home Screen: the ⋯ row, the one-time banner, and the steps sheet both open. |
| `immersive.js` | Pad+Flip+player+library+gallery+in-post+host gallery | Full size on the devices that have a Fullscreen API, and on the one that does not. |
| `inputlog.js` | Pad+Flip | The input log: what the screen said, for a bug only a phone shows. |
| `inputsamples.js` | Pad+Flip | The points the browser already captured and the handler was throwing away. |
| `keyregistry.js` | Flip | lib/keyregistry.js — what is bound to which key, and whether two things answer at once. |
| `labels.js` | Pad+Flip+library+gallery+host gallery | WORDS IN A BUTTON SIT IN THE MIDDLE BY THEIR CAPITALS, in any font. |
| `learncard.js` | Pad+Flip | The card on the button: help where the question is (owner, after v323: "Can we combine them so we get the best, most helpful yet unobtrusive?", then "All yes" to the button cards mock). |
| `looptrim.js` | Pad+Flip+player | Loop trim clamping — the rule both editors apply six times between them. |
| `lostlift.js` | Pad+Flip | A stroke whose lift never came — the two editors only, never the player. |
| `marks.js` | Pad+Flip+library+gallery | The app's marks for controls a script builds: plus, minus, close, check, arrow, chev, cloned from the <template id="skriblMark-NAME"> that _skribl_marks.html puts on the page, so a script and a template draw the same mark from one source. |
| `media_validation.js` | Pad+Flip | media_validation.js — one owner for media format policy and byte verification. |
| `mediatabs.js` | Pad+Flip | The Media button and its Photo and Music tabs -- shared by Pad and Flip. |
| `menupages.js` | Pad+Flip | The ⋯ menu's pages: the main page, New Skribl and Settings, one sheet (templates/skribl/_skribl_menu.html; owner, after v323, from the menu mock). |
| `mirror.js` | Pad+Flip | Mirror drawing — reflect each point across the canvas centre, shared by both. |
| `modalfocus.js` | Pad+Flip+library+gallery+host gallery | Focus for surfaces that declare aria-modal="true". |
| `mp4export.js` | Pad+Flip | MP4 export through WebCodecs + the vendored mp4-muxer: one encoder pipeline for both editors (SK312-003, v315). |
| `musicdrawer.js` | Pad+Flip | THE MUSIC DRAWER'S CONTROLS, one copy for the Pad and for Flip. |
| `musicears.js` | Pad+Flip | SKRIBL'S EARS: where a song's beat falls, how many beats make its bar (four, or three), which beat starts one, and which stretch of whole bars comes round most smoothly. |
| `musicrestart.js` | Pad+Flip | THE RESTART VIEW: the loop's end beside its start, behind the music drawer's Restart door, to line the beats up across the join by eye and pull a smooth restart's blend longer or shorter. |
| `musictimeline.js` | Pad+Flip | THE TIMELINE: the music drawer's one view of the loop, on the Pad and on Flip, the drawing's lane above the song, the loop's two ends as handles, and the whole song as one thin line under them. |
| `nametab.js` | Pad+Flip+library | The skribl NAME drawer — a title for the drawing, shared by Pad and Flip. |
| `newundo.js` | Pad+Flip | NEW SKRIBL, AND THE WAY BACK: one offer for both editors. |
| `nib.js` | Pad+Flip | The glowing dot that rides the tip of a line while it draws itself: its colour, and its picture in a file. |
| `offline.js` | Pad+Flip+library | The Home Screen app: opening with no signal, and staying current. |
| `opensurfaces.js` | Pad+Flip+library+gallery | What is open, said once on <html>, so no style rule has to search the page. |
| `othertab.js` | Pad+Flip | TWO TABS, TWO DRAWINGS, NOTHING LOST (SK-AUD-006; the owner's pick T1). |
| `pagemenu.js` | library+gallery | The page menu: the ••• on the gallery and the library, and what it opens. |
| `pagespan.js` | Flip | Page spans — a contiguous run of Flip pages, and the operations on it. |
| `painttarget.js` | Pad+Flip | The draw drawer's paint-target seg (Pen or Background): wired once for both editors (SK312-003, v315). |
| `palette.js` | Pad+Flip | The pen palette — one list, both editors. |
| `pendingcards.js` | Pad+Flip | The file rows of the Photo and Music drawers -- the drop area until a file is added, then the file itself and its bin -- with the "re-add your file" cards and the tab dots that hint media is waiting: one implementation for both editors. |
| `penswoosh.js` | Pad+Flip | The pen SWOOSH — the pen button drawn as the stroke it will make. |
| `photofit.js` | Pad+Flip+library+in-post | Photo fit geometry — the part both editors and the player must agree on. |
| `pillfit.js` | Pad+Flip | The autosave pill yields to the controls it would sit on. |
| `pinchgesture.js` | Pad+Flip | Pinch contact tracking — the two editors only, never the player. |
| `pointbudget.js` | Pad+Flip | The DOCUMENT's budget — the numbers the editors were spending without being able to see them. |
| `pointpack.js` | Pad+Flip | A LONG DRAWING, PACKED: the compact form both editors' autosaves keep their points in once a drawing is long (v322 plan, step 1). |
| `pointwrite.js` | Pad+Flip+face | How a point is WRITTEN — the shared rule for both editors' serializers. |
| `posted.js` | Pad+Flip+library | Your Skribls — a local record of what you have posted. |
| `postedaudio.js` | Pad+Flip | What a POST stores, which is deliberately not what an EXPORT downloads. |
| `postedcard.js` | Pad+Flip+face | Compositing /s/<id>/card.png — the post-time half of lib/sharecard.js. |
| `postedui.js` | library+gallery+host gallery | Your Skribls — rendering. |
| `postfull.js` | in-post | A post's full screen: the button at the end of a post's line opens the link page's full screen around the post's own player. |
| `postsheet.js` | Pad+Flip | The Post sheet — shared by Pad and Flip (skribl/_skribl_post.html). |
| `pressure.js` | Pad+Flip | Stylus pressure — the curve, the floor, and the on/off, shared by both editors. |
| `recentcolors.js` | Pad+Flip | Recent colours — the first controller shared by both editors. |
| `recolor.js` | Pad+Flip | Recolor: a line already drawn takes a new colour (the owner, of the mock: "I love the recolor too", every choice yes). |
| `recolorplay.js` | Pad+Flip+player+in-post | A recolour in the replay (the owner's pick R2 of the recolour mock: the Pad's replay shows the change when you made it). |
| `recoverykey.js` | Pad+Flip+library | Both ends of an anonymous author's revocation key: showing one, taking one back, and standing between a bulk clear and the keys it would discard. |
| `replayline.js` | Pad+player+library+in-post | How fast a replay runs, and the line that says what you are watching. |
| `report.js` | Pad+Flip+library+gallery | "Report a problem" — the context, collected once, for both editors. |
| `savedrafts.js` | Pad+Flip+library | Saved drafts — ⋯ "Save draft" and "Open a draft…" on both editors (v316), and the Library's Drafts tab (v317). |
| `scrubkeys.js` | Pad+Flip+player+library+in-post | Keyboard operation and live value for the three playback scrubbers. |
| `seekcache.js` | Pad+player+library+in-post | SCRUBBING STARTS NEAR WHERE YOU POINT: a few snapshots of a replay's canvas, so a seek draws only what lies between the nearest one and the target (v322 plan, step 3). |
| `segslider.js` | Pad+Flip+library+gallery+host gallery | THE PILL. Every pick-one control in the product slides one soft tint under its selected option, and this is the one thing that places it (the owner, choosing between four mocked shapes: "a on the pill"). |
| `selection.js` | Pad+Flip | Selection — pick a region, then move what is inside it. |
| `shapecard.js` | Pad+Flip | The shape card -- the picker that opens above the Shape tool -- one implementation, both editors. |
| `shapes.js` | Pad+Flip | Shapes — line, rectangle and ellipse, expressed as ordinary stroke points. |
| `sharecard.js` | Pad+Flip+library+face | /s/<id>/card.png: WHERE THE DRAWING SITS INSIDE IT. |
| `sheetswipe.js` | Pad+Flip+library+gallery+host gallery | Sheets that go away — one swipe, every bottom sheet. |
| `sizeclass.js` | Flip | One size decision, made once, for the whole app. |
| `slidernudge.js` | Pad+Flip | - and + beside a range slider, for exact steps a slider alone cannot land on with a finger. |
| `smartfade.js` | Pad+Flip+player+library+gallery+in-post+host gallery | The smart fade: one reading of a drawing for every bar that lies over it. |
| `smoothing.js` | Pad+Flip | Smoothing (the stroke stabilizer) — shared by both editors. |
| `songtext.js` | Pad+Flip | A SONG'S TEXT, MADE OFF THE PAGE: the data URL both editors keep beside a song's bytes, made in a worker so that adding a song does not hold the page while it is made (the speed fixes, Nov 5; the owner: "do the song speed for both editors"). |
| `stamps.js` | Flip | Stamps — the clipboard, but named, persistent and multi-slot. |
| `strokelayers.js` | Pad+Flip+player | Stroke layers — the see-through-stroke compositor's on/off, shared by both. |
| `tappause.js` | Pad+Flip+player | Tap to pause: a tap on a drawing while it plays -- an editor's preview, or the shared player -- pauses it where it is, and another tap carries on from there. |
| `textwrite.js` | Pad+Flip | TEXT: words that write themselves (FUTURE.md 6ab). |
| `theme.js` | Pad+Flip+library+gallery | Light/dark chrome — the stored setting, and the one place that applies it. |
| `toolscroll.js` | Pad+Flip | The toolbar on the smallest screens -- Pad's, and Flip's since the dock redesign: one row that scrolls, and says so. |
| `toolshelf.js` | Pad+Flip | Tool shelf + overflow tray — shared by Pad and Flip. |
| `tooltip.js` | Pad+Flip+library+gallery+host gallery | Styled tooltips, replacing the browser's. |
| `videorecord.js` | Pad+Flip | The video both editors make where WebCodecs cannot make an MP4: ONE exporter. |
| `watchfull.js` | Pad+Flip | Full screen in the editors: the drawing as big as the screen goes, while it plays. |
<!-- /GEN:MODULE-INDEX -->

Generated by `harness/gen_docs.py`: the surfaces come from the templates that
load each module and the description is the module's own opening sentence, so
neither can drift from the thing it describes.

Two are worth calling out because they were extracted after a bug, not before:
`holdtiming.js` (the editor and the player disagreed about what a hold means,
and one release later four surfaces disagreed about what a reveal shows at its
first frame)
and the budget inside `strokelayers.js` (the editor capped its compositing cost
and the player did not). Both are covered by `verify_sharedrules.py`.

## Known-open, in the order worth doing

The owner's open decisions are the "Still open" list at the end of the latest
seal's entry in DECISIONS.md; ideas for later are in FUTURE.md.

### First after the seal and its outside audit: the owner's device check

The owner checking the build on an iPhone (Safari, the Home Screen app,
VoiceOver) and on Windows, from a checklist of what to screenshot and what to
look for. It has been carried as still open at every seal since v318, because
neither device's fonts nor its engine exist in this container. Skipped for the
seal after v320 at the owner's word, with this instruction: raise it as one of
the first things once that seal and its audit are done. Refresh the checklist
for the build as sealed before offering it.

Put on its checklist Blooby around the app (FUTURE 6l), which the owner asked
about in that cleanup and parked until after the audit: he is built now, his
pen on the empty canvas, his question mark where a drawing can't be shown, his
cheer after a post, and the owner has seen each only in mocks made here.

### Closed: the bottom-toolbar redesign

The proposal was a labelled "Tools" sheet holding Image, Music and Magnify, and
it left two questions it never settled: where Undo and Redo go once they leave
the bar, and whether Image and Music belong in "Tools" at all, being content
rather than tools. The dock the owner chose instead answered both (#271 on):
Undo and Redo stayed in it, and Image and Music became one Media button. The
pen, eraser and shape sit on it with More tools beside them, and Magnify shows
on a desk, where there is room. The measurements the proposal argued from are
in git history, and were already out of date when this section closed.

## Things that will bite an unwary helper

* **NEVER edit a released Alembic migration.** `RELEASED.txt` freezes every
  digest and `verify_migrations.py` fails if one changes.
* **A screenshot Cal renders is one Cal has seen, not the
  owner.** Measure it; do not describe it as shown. The owner's phone
  screenshots run the other way and are the bug reports
  (`docs/SESSION-CONTEXT.md` §7).
* **Measure rendered geometry, not arithmetic.** Flex shrinks controls before
  anything overflows, so summing child widths reports room that is not there.
  Force the candidate into the DOM and read `scrollWidth` against
  `clientWidth`. Likewise `offsetParent`, not the `hidden` property.
* **An explicit `display` defeats `[hidden]`.** Hit three times. Scope layout
  rules with `:not([hidden])` or pair them with `[hidden]{display:none}`.
* **`classList.toggle(name, undefined)` TOGGLES.** An `&&` chain that can yield
  undefined must be wrapped in `!!` — this made two colour swatches appear
  selected at once.
* **An inline style beats any stylesheet rule.** `setTool()` writes
  `pad.style.cursor` inline, so cursor changes must also be inline.
* **Top-level `let` is not on `window`.** `window.frames` is the browser's
  frame collection and `window.fps` is the element with `id="fps"`. Read
  editor state through a bare identifier, not off `window`.
* **A retry must accept on the property the assertion checks.** A WebM test
  retried on byte count and asserted on duration; it flaked three times.
* **Both editors draw on Pointer Events (Pad since v315, SK312-002); the pinch
  is on touch events in both.** The trap that remains: a stroke's pointerdown is
  prevented, which suppresses the compatibility MOUSE events for that press, so
  a `mousemove`/`mouseup` listener hung off a canvas stroke never fires.
  `verify_pointerpad.py` drives each such listener with real input.
* **Finish all documentation BEFORE the final harness run.** `run_harness.sh`
  calls `stamp_docs.py` itself, and the run recorded LAST is the one stamped —
  so the recorded set must be the final invocation. Regenerate `SHA256SUMS`
  after, and delete any scratch probe suite first or it ships.
* **A skip is not coverage.**

---

## Running it

    pip install -r constraints.txt --require-hashes    # the pinned lock
    python -m alembic upgrade head                     # NOT create_all()
    gunicorn app:app

`gunicorn` reads `gunicorn.conf.py` from the repo root by its name: 8 threads a
worker (`GUNICORN_THREADS` changes it), so an editor's first open of about 120
files is not answered one file at a time. `WEB_CONCURRENCY` still sets the
number of workers. Each worker also strips and compresses every Skribl file
before it takes a request (`skribl.warm_assets`, a few seconds; the log says
how many files and how long), so the first visitor after a deploy does not
wait for it. The stand-in that `app.py` mounts at `/host` (examples/host_app,
with a Skribl of its own) is warmed after that, on a thread that rests after
each file, so the demo's own visitors are not held for it. The site at
`/social` shares the demo's Skribl, whose files are the ones warmed first
(`SKRIBL_SOCIAL=0` leaves it out); its own tables are on a migration chain of
their own, which `gunicorn.conf.py`'s `on_starting` brings up to date once,
in gunicorn's master before any worker loads the app
(`python -m alembic -c social/alembic.ini upgrade head` by hand). A site chain
that fails or takes over two minutes is logged and left: the demo serves, and
the site's sign-in answers a kind 503 until its tables are there.

On Render, the middle two run together from the dashboard **Start Command**
(`python -m alembic upgrade head && gunicorn app:app`) — set in v270, when it
emerged that Render never reads the `Procfile` v267 had wired the same line
into, and production had therefore never run a migration on deploy (DECISIONS
v270). The Procfile keeps the same command for Heroku-style hosts and as local
reference only. Neither needs a word for the site's chain: both start gunicorn,
which runs it. If you ever run more than one web instance, move both migrates
to a Render `preDeployCommand` so two boots cannot race the same `upgrade head`.

    ./harness/run_harness.sh verify_move.py            # name them, or run bare for everything
    python3 harness/stamp_docs.py                      # docs from LAST-RUN.txt

`pip install -r requirements.txt` also works. What does NOT work is
`-r requirements.txt -c constraints.txt` — the lock carries hashes, which puts
pip in `--require-hashes` mode, and that mode rejects version ranges.

---

## A note on process

Almost every bug this session was found by RUNNING something, after the code
read correctly — and several were found by the owner on a real phone after the
suite was green. Screenshots caught what assertions did not: a canvas picker
that painted a purple bar over its own menu passed 21/21 first.

What a phone catches and a headless browser cannot is written down as
`docs/DEVICE-CHECKLIST.md` — about fifteen minutes on an iPhone, before a
release that will be shown to people and after any change to input, audio,
zoom or text size.

The pattern worth carrying: **when a change touches a surface, write the
assertion that reproduces the OLD behaviour first**, and prefer measuring what
is rendered over what the code was told to do.
