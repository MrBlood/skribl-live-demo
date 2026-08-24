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
