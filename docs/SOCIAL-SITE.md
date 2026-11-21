# The Skribl social site: how it is laid out

**Status: agreed, Nov 10. The owner said "all yes" to every default in
section 8.** Nothing here is built yet except where it says "have", and phase
1's first piece, the frame, which section 9 describes.

**The map since Nov 13 is section 16**: a post is the one thing people
share. Where an earlier section says otherwise (Home holding every drawing,
what Explore and a profile show, no follower counts), section 16 is the
decision. **Its part two, since Nov 14, is section 17**: what any social site
has (bookmarks, reposts and quote posts, mentions, finding people, open
sign-up, push notifications, direct messages), in the owner's order, and one
drawing, one conversation. **Since Nov 17, section 18**: the comment
thread (bubbles, the post's choices on every comment, every list one level
of direct replies, each opening its own page), the owner's yes; step 1
built.

The owner, Nov 10: "we are beginning to build the social media site, so we
need to take care to keep it straight. This may be the beginning of a social
media site that will have millions of users, so keep scale in mind and be
cognizant of all the functions of a social media site... Let's lay this out
well so we don't have to later fix stuff... I hope we can just drop the
pad/flip into skribls.net, but we may have to go it alone and create the
entire site... Let's do this right."

FUTURE.md §3 said to back into a network rather than aim at it, and 6ah said
Skribl must always be able to be its own site. This is the moment of aiming,
on purpose, without giving up the other door.

---

## 1. The one rule that keeps it straight: three layers

| Layer | What it owns | Where it lives |
|---|---|---|
| **Skribl** | Everything about a drawing: Pad, Flip, the players, a skribl's own page, the Gallery and its card, drafts, reports and takedowns of drawings, media storage, the posting API. People are an opaque id it is handed. | the `skribl` package (have) |
| **The site** | Everything about people: accounts, sign-in, profiles, follows, feeds, comments, likes, notifications, settings, moderation of people and words, legal pages, admin. | a new app, `social/`, beside Skribl (working name) |
| **Hosts** | A site that mounts Skribl. skribls.net would be one; our own site is another; `examples/host_app` stays the small worked example (and the stand-in at /host). | wherever each lives |

**The site is a host of Skribl, through the same public seams any host uses**
(`init_skribl`, `create_post`, the author and source resolvers, the
`skribl_inline` macros, the listing API: docs/INTEGRATION.md). It reaches
nothing else inside Skribl, and Skribl never imports the site. A check will
hold both directions, the way `verify_deletion_foundation` holds Skribl to its
own database seam.

Why this shape:

- **If skribls.net says yes,** Pad, Flip and the Gallery drop in exactly as
  they do today, and the site's people-features that skribls.net already has
  simply are not used. **If it says no,** our site is the host. Either way,
  nothing gets ripped out.
- **Anything our site needs from Skribl, every host gets.** The Gallery card
  as a piece a page can embed (the owner's B) is the first example: built for
  our site, usable by skribls.net the same day.
- **Not grown inside `examples/host_app`.** That is a teaching example a few
  hundred lines long; it shows skribls.net how to mount Skribl. Growing the
  real site inside it would bury the lesson and tie the two together.

---

## 2. What a social site has, and what Skribl has already

Phase numbers are section 5's.

| Area | The pieces | Have today | Phase |
|---|---|---|---|
| Accounts | sign up, sign in and out, passkeys, a link by email for a new device, handles, email check, sessions and devices, delete my account, download my data, minimum age | none of its own: identity comes from the host (the demo's stands in) | 1 |
| Profiles | a page per person, a drawn avatar (that draws itself), a few lines about them, links, their skribls, a pinned one | a person's skribls through the listing | 1 |
| Posts | words plus a skribl (or several), edit, delete, who can see it (everyone, followers, link only, just me) | skribls with three visibilities, revocable deletion, account drafts | 1 |
| People | follow, followers, block, mute; later, private accounts that approve followers | none | 2 |
| Feeds | Following (newest first), Explore (the Gallery's New and Hot), a profile's own; later "For you" | Gallery New, Hot, search | 2 |
| Talking | comments and replies, reply with a skribl (FUTURE §4 idea 7), mentions, likes, repost | plays are counted | 2-3 |
| Notifications | an in-app list with an unread count, push to the Home Screen app, email digests, a switch per kind | none | 2-3 |
| Finding things | search people, skribls and tags; hashtags; what is popular | search of titles and captions | 3 |
| Safety | report anything, a moderation queue and tools, block and mute, limits per account, spam signals, takedowns, appeals, suspending an account | reports and takedowns of skribls, limits per address | 1 (basics), then every phase |
| The law | terms, privacy policy, community guidelines, a DMCA agent, the duty to report child abuse imagery (US law), age rules, data export and deletion | Skribl's deletion is real and tested | 1, before public sign-ups |
| Creators | plays, then editions, rights and prints as an artists' co-op (FUTURE 6ag) | plays | 4 |
| Messages | private messages between people | none | later, on purpose |
| Admin | look up a person or post, act on reports, a record of every action taken | Skribl's takedown tools | 1 (small) |
| Apps | Home Screen app, then native apps, both on one versioned API | the Home Screen app | later |
| Other networks | Bluesky and Mastodon can see and follow Skribl people | share cards already unfurl there | later |

**Private messages wait on purpose.** They are where harassment and grooming
happen out of sight, so they carry the heaviest safety cost of anything on
the list. They come after the moderation tools have earned trust.

---

## 3. Built for millions, paid for thousands

These are the choices that are cheap to make now and expensive to change
later. They cost nearly nothing at today's size. The expensive machinery
(caches, replicas, splitting the database) waits until a measurement asks for
it, behind interfaces that do not change when it comes.

1. **Ids.** Public ids are random and opaque (have). Internal ids are 64-bit
   from the first table. Nothing exposes a counting id, which would tell the
   world how many people or posts there are.
2. **Every list pages by cursor, with a hard limit.** Never "skip the first
   N", which gets slower with every page (the listing does this already).
3. **Counts are kept, not counted.** Likes, followers and plays are stored
   numbers, updated as things happen (plays already keep a running total),
   never counted row by row when a page is viewed.
4. **Drawings and media live outside the database,** in object storage behind
   a CDN, a network of servers near the viewer. Skribl's S3 store is built
   and tested; switching it on costs money and waits for a yes. Lists never
   read a drawing's payload (the listing already leaves it out).
5. **Slow work goes to a queue.** Notifications, feed updates, emails,
   thumbnails, abuse scanning and deletions are recorded by the page and done
   by a separate worker. A web page never waits on them. It starts as a jobs
   table in PostgreSQL; a background worker on Render costs money and waits
   for a yes.
6. **Feeds start simple, behind an interface that will not change.** First,
   "pull": the Following feed is read from the newest posts of the people you
   follow, on indexes built for it. That is right up to a few hundred
   thousand people. Then "push": each post is written into its followers'
   stored feeds when it is made, with very large accounts still pulled. The
   feed's API stays the same through the change.
7. **Web servers remember nothing between requests.** Sessions are signed
   cookies or rows; anything shared (limits, caches) is in PostgreSQL now and
   a cache server later. So more servers can be added at any time.
8. **Every table is written with its indexes,** and every new query's plan is
   checked in its suite, the way Skribl's listing is timed today.
9. **Deleting is real.** A short undo window, then a job that removes the
   rows and the files. Deleting an account removes its posts, media, likes and
   follows. Skribl's deletion module already works this way and is tested.
10. **Private by default.** Everything posted has a visibility, and nothing
    becomes public as a side effect.
11. **Everything that can be abused has a limit,** per person and per
    address (Skribl's limiter already counts per address, on PostgreSQL,
    across workers).
12. **One versioned API** (`/api/v1/...`) that the site's own pages use and
    native apps will use later.
13. **Times are stored in UTC** and shown in the person's own time zone.
14. **Words live in one place per page,** so translating the site later is
    work and not a rewrite. No translating now.
15. **Errors and slow queries are watched from the first day.** Free tiers
    first; a paid service waits for a yes.

**The stack stays:** Python, Flask and PostgreSQL. Instagram grew to hundreds
of millions of people on Python and PostgreSQL. At that size the problems are
the shape of the data and the work, which is what the list above is for, not
the language.

---

## 4. Where it runs

Today: one Render Starter instance, SQLite for tests, PostgreSQL in CI and
on the live demo. As it grows, roughly in this order, each step costing money
and so waiting for the owner's yes with an estimate (WORKING-AGREEMENTS,
"Spending"): object storage and a CDN for media; a background worker; a
bigger database; a cache server; more web servers. None are needed for
phases 1 and 2 with a few hundred people.

**The setup Cal recommends for the long run (Nov 10, asked by the owner):
Render and Cloudflare.** Render keeps running the app and its PostgreSQL
(no server to patch or back up by hand; the harness and the deploy already
target it), with a background worker added when the job queue arrives.
Cloudflare holds the domain (its registrar sells at cost), its DNS, the CDN
in front, R2 for drawings and music (S3-compatible, so Skribl's S3 store
works with it, and no fees for downloads), and Email Routing for a free
hello@ address. A sending service (Resend or Postmark) comes with the
emailed sign-in link, and Sentry's free tier watches for errors. A rented
server would be cheaper on paper and is a second job: no. Prices were given
to the owner from memory, flagged as such (this container cannot reach those
sites): roughly $15 to $25 a month plus the domain at first, $50 to $100 a
month at thousands of people. Each step waits for the owner's yes.

Asked again on Nov 10 ("Is it cheapest to keep Render?"), and checked by a
web search this time (Fly's own pages; 2026 price round-ups for Render and
Railway, whose pages could not be read from here): yes, for a setup with no
server to keep by hand. The demo is about $13 a month (Starter $7, Postgres
Basic $6). Fly's app would be cheaper, but its managed PostgreSQL starts at
$38 a month; Railway meters an app and its database at about $15 to $22,
and the bill moves; Render's free plans sleep and expire (the free database
already did once). Worth asking again at thousands of people, or a bill
near $50 to $100.

---

## 5. The phases

Each phase ends with something people can use, tested the way everything
here is tested (a check shown red before it is believed).

- **Phase 0, now.** This layout, and the owner's B: Skribl's Gallery card as
  a piece any page can embed, used first by the stand-in's Skribls tab. It is
  the first building block for both doors. *Have (after v330):* the whole
  Gallery section, `skribl_gallery_section()` with `skribl_gallery_assets()`
  (docs/INTEGRATION.md, "Skribl's own Gallery on your page").
- **Phase 1, foundations.** The site's skeleton (`social/`), mounted on the
  demo at an address of its own, with Skribl mounted inside it as a host;
  accounts and sign-in; profiles with a drawn avatar; posts with skribls;
  report anything, the admin's queue, block; the legal pages in draft; media
  to object storage (when said yes to).

  **Its look, the owner's "all yes" on the mocks (Nov 10):** A, Sketchbook
  (the tokens the Gallery, the Library and the editors' sheets already wear,
  plus a pen's touch); a rail down the left on a desk, a bar along the
  bottom on a phone; Make opens a small sheet with two doors, Draw and Flip;
  faces that are skribls and draw themselves once on a profile; a post that
  starts by itself on its own page (sound off, never under Reduce Motion);
  and a first visit where Blooby draws his card above the newest skribls.
  The mocks: https://claude.ai/artifact/6uHGpDeSxheJusXK8iqL1N.

  **One Skribl, shared.** A drawing made in the Pad is a skribl on the site,
  and the site's people are the people the Pad posts as. So `social/` is a
  package the host process plugs in beside Skribl (`init_social(app)`, at
  /social on the demo), not a second Skribl: one database, the site's tables
  under their own names (`social_...`) with their own migration chain, so
  Skribl's chain and Skribl alone are untouched. It still reaches Skribl only
  through the public seams, and Skribl never imports it. Once the site has a
  domain, the same process answers there with the site at the top.

  **The build order, one piece at a time, each something to look at:**
  1. *The frame, read-only.* `social/` at /social: the Sketchbook look, the
     bar and the rail, Home as the first visit (Blooby's card above the
     newest public skribls), Explore as the Gallery section, Make's sheet
     into the Pad and Flip. No accounts yet, so no You.
  2. *Sign-in.* Accounts with passkeys and an emailed link, 13 and over;
     the site's people become the people the Pad posts as. Asks first: the
     email service (it may cost), and the domain (passkeys are tied to the
     address they are made on). *The owner's "all yes" (Nov 10):* built on
     the demo's address first, for invited people (their passkeys are made
     again after the move to the domain); passkeys alone first, the emailed
     link once an email service is picked and its price compared;
     invite-only until a lawyer has read the terms.
  3. *Profiles and drawn faces.* "Draw your face", a face that draws itself
     once (a small new Skribl piece, the face player), the person's skribls.
  4. *Posts.* Words and a skribl, posted from the site; a post's own page
     that starts by itself; the ⋯ with Report.
  5. *Safety.* Report anything, the admin's queue, block; the legal pages
     in draft.
  6. *Media to storage.* When the owner says yes to its cost.

  *Built and live on the demo by Nov 10: pieces 1, 2 and 3 (section 9).
  Piece 4 is next.*
- **Phase 2, the social core.** Follow, the Following feed, comments and
  replies, likes, in-app notifications, mute. *Comments and their answers
  built Nov 12 (section 10); in-app notifications (Activity) the same day
  (section 11); likes Nov 13, their dots on the line and the hearts that
  rise from them the same day (section 12); follows and Home's Following the
  same day (section 13).*
- **Phase 3, growing.** Search and tags, push and email notifications, reply
  with a skribl, repost, invite links.
- **Phase 4, creators.** Editions, rights and prints, the co-op (FUTURE 6ag).
- **Later.** Private messages, other networks, native apps, "For you".

Pad and Flip keep evolving through all of it. They are why anyone comes.

---

## 6. What does not change

Skribl Pad first: watching a drawing come alive is the point of the whole
site. Powerful, playful, simple and kind, in every phase; kind especially
where safety is concerned (nothing a person makes is lost by mistake, and a
person is never blamed by the words on the screen). Pad and Flip move
together. Skribl stands alone; the site borrows it like any other host. Every
change is checked, and every check is shown red first.

The owner, Nov 10, the evening the first person joined: "Don't lose track of
our roots and evolution of kindness and our 4 pillars. Keep our vision." So
every piece, its mock and its PR answer two things in plain words before it
is built and again when it is shown:

- **The roots:** what it does for watching a drawing come alive (a face that
  draws itself, a post that starts on its own page, the drawing as the
  biggest thing on the screen). A piece that does nothing for it says so,
  and why it is still needed.
- **The four pillars, kind first:** one line each for kind, powerful,
  playful and simple. The owner, the same evening: "Make it make sense.
  Simple and kind means intuitive and fun." So simple is checked as "would a
  person get it without being told?", and kind as "does it feel good to
  use?", not only "is it short?" and "is it polite?". Kind is checked on the hard paths, not only the happy
  one: what a person sees when something does not work (the words never
  blame and always say what to do next), when they are new, and when they
  want to leave (nothing they made is lost by mistake, and going is easy).

The first evening showed where kind gets lost: a sign-in page that said "No
passkey was picked" to someone who had not joined yet, and instructions that
called an invite code a passkey. Fixing those words comes before new
screens.

---

## 7. The honest part

- **Moderation is a job for people, every day, forever.** Code makes it
  possible; it does not make it happen. Someone has to read the reports.
- **A lawyer reads the terms and privacy policy before public sign-ups,** and
  the child-safety reporting and DMCA agent are set up first. Cal can draft;
  Cal cannot sign off on the law.
- **A network needs people** (FUTURE §7). The first few hundred matter more
  than the millionth.
- **Cost grows with use.** Each step in section 4 is asked about first.

---

## 8. The owner's decisions

The owner answered "all yes" on Nov 10: every default below is the decision.

1. **Three layers:** the site is its own app, `social/`, beside Skribl, and is
   a host of Skribl through the public seams only. Not grown inside
   `examples/host_app`. *Default: yes.*
2. **The stand-in at /host stays the skribls.net stand-in;** the site gets its
   own address on the demo until it has a domain. *Default: yes.* The
   address, the owner's yes (Nov 10): **/social** on the demo
   (skribl-live-demo.onrender.com/social).
3. **Name and domain:** the owner's call. *Default: "Skribl" for now, domain
   later.*
   **A domain is best bought before sign-in is built (phase 1).** Passkeys
   are tied to the address they are made on, so passkeys made on the demo's
   address would have to be made again after a move; a Home Screen icon
   saved from the demo stays tied to the demo's address too; and the emailed
   sign-in links are best sent from the site's own domain. What the owner
   sets up then: the domain itself (auto-renew and two-step sign-in on the
   registrar's account), the domain added to the Render service (Render
   shows the DNS records to add and makes the HTTPS certificate), the site's
   own addresses in Render's Environment (`SKRIBL_SOCIAL_HOSTS`: the domain,
   and the demo's name while people move over), and later the email
   service's few DNS records. What Cal sets up: the site answering
   at the top of the new domain while the demo keeps its own address, and
   the checks that both answer (built Nov 11 for blooby.app: "The move to
   blooby.app", below).
4. **Sign-in:** passkeys (Face ID, Windows Hello), with a link by email for a
   new device; no passwords to leak. Sending email needs a service (a free
   tier is likely enough at first; asked at phase 1). *Default: yes.*
5. **Minimum age 13.** *Default: yes.*
6. **Private messages later,** not in phases 1 to 3. *Default: yes.*
7. **The phase order above,** B first. *Default: yes.*
8. **No public sign-ups before** a lawyer has read the terms and privacy
   policy and child-safety reporting is set up. Building and testing with
   invited people can start before that. *Default: yes.*

**And one more, asked later the same day.** The owner: "can we try to
duplicate skribls.net? ... or should we just build our own. maybe just
building our own would be better." Then "all yes":

9. **Build our own, not a copy of skribls.net.** A saved page holds only the
   outside of a site (its look and its scripts); the accounts, database,
   feeds and moderation run on its server, so a copy saves the easy part and
   none of the hard part. A copy would also bring its problems with it (the
   ones docs/SKRIBLS-NET.md records), would make the scale rules in section 3
   a retrofit, and is not ours to make: someone else decides what happens on
   skribls.net. Features belong to no one, so its saved pages stay welcome as
   a checklist of what a page needs, and they keep the drop-in door tested
   through the stand-in. Phase 1's mocks start from Skribl's own look.

---

## 9. Built: phase 1, piece 1, the frame

The site's frame, read-only, in the owner's A (Sketchbook), at **/social** on
the demo. `social/` is its package: `init_social(app)` in
`social/__init__.py`, its pages in `social/templates/social/`, its own files
in `social/static/`. The demo's `app.py` plugs it into its own app right after
`init_skribl`, so the site and the Pad share one Skribl and one database.
`SKRIBL_SOCIAL=0` leaves it out, and a site that cannot start is logged and
left out: the demo never depends on it.

| Where | What it is |
|---|---|
| `/social/` | **Home.** For now the first visit, for everyone: Blooby draws his card (How it works' own Flip, in Skribl's own player, resting finished under Reduce Motion), "Drawings that draw themselves", **Make a skribl** and **Look around**, and the newest public skribls under it, in Skribl's own Gallery section. |
| `/social/explore` | **Explore:** Skribl's own Gallery section, New and Hot, search, Report, Load more. A card opens the drawing's page here from anywhere on it (`/social/b/<id>`, on to its post where it is a post's; "Every card opens its post", below). |
| Make | Not a page: a small sheet with two doors, **Draw** (Skribl's Pad) and **Flip** (Skribl's Flip), from the bar on a phone, the rail on a desk and Home's button. |

A phone has a bar along the bottom (Home, Explore, Make; You comes with
sign-in; Explore is the Gallery since section 16's step 3), a desk a rail
down the left (the wordmark in the accent purple, Home, Explore, Make), and
the page you are on has a pen's line under its name. SINCE NOV 15 (the
owner's G: "Can all icons look the same size - bigger", then "I like g") the
phone's bar is its icons alone, no words under them (each place's name still
its accessible name), Make's purple and your face round and 32 across, and
the line drawings (the house, Blooby, Sign in's person) at 92% of the 28px
square they first filled, the house 25 x 24 of ink and Blooby 23 x 26 (the
owner: "Home and gallery (unselected) look a little big"); Blooby lit on the
dark bar is drawn at 96%, where his black line is lost to the ground
(DECISIONS, "The bar: Home and the Gallery at 92%"). The pen's line sits
under the page's icon; the desk's rail keeps its words. Light and dark
followed the device here; since Settings (section 14) the site wears
Skribl's own one choice, for Blooby, Pad and Flip alike.

It reaches Skribl only through the seams any host uses: the in-post player's
and the Gallery section's macros, Skribl's signature (now documented for every
host, docs/INTEGRATION.md), `skribl_asset()`, and the addresses of the Pad and
Flip. It imports nothing from the `skribl` package, and Skribl never imports
it. Its pages carry their own security policy (every script a file), and ask
for Skribl's fade between pages, so going into the Pad and back is a fade, not
a cut. Pad and Flip are unchanged: Make opens them as they are.

`harness/verify_social.py` holds all of it through the demo's own server, and
DECISIONS.md ("The site's frame at /social") says what each check was shown
red by. Not yet, on purpose: accounts and You, posts, and tables (when they
come, named `social_...` with their own migration chain).

### Built: piece 2, sign-in (invite-only, passkeys)

The owner's answers, built: on the demo's own address for invited people
(each passkey keeps the address it was made on, and nothing names a host, so
after the move to a domain people make theirs again), passkeys alone (no
email yet), 13 and over, invite-only.

| Where | What it is |
|---|---|
| `/social/join#<code>` | **Join**, from an invite link: a name, a handle, "I'm 13 or older", a passkey; signed in. The code is after the `#`, which a browser never sends to a server, so no log holds it: the page posts it to `/join/check`, then `/join/options` and `/join/verify`. A link that does not work (used, run out, revoked, never made) gets one kind card, and the server one answer. |
| `/social/signin` | **Sign in with a passkey**: nothing typed (`/signin/options`, `/signin/verify`). Sign out is a button (`/signout`); so is **Sign out everywhere** (`/signout/everywhere`). |
| `/social/you` | **You**: name and handle, the passkeys (add another: `/you/passkeys/options`, `/you/passkeys/verify`; rename and remove: `/you/passkeys/<key_id>/rename`, `/you/passkeys/<key_id>/remove`, never the last), signing out, and **Delete my account** (`/you/delete`). In the bar on a phone, at the rail's foot on a desk, once signed in; Sign in in its place before. |
| `/social/invites` | **Invites**, admins only (a 404 like any missing page to anyone else): a join link (once, 14 days), a recovery link for a named person (`/invites/recover`: once, an hour, adds a passkey to their account), the unused ones, revoke (`/invites/<invite_id>/revoke`). |
| `/social/recover#<code>` | **A recovery link**: names whose account it is for (`/recover/check`), makes a passkey there and signs in (`/recover/options`, `/recover/verify`). The stand-in for an emailed link until there is email. |

**The first person.** `SKRIBL_SOCIAL_FIRST_INVITE` is an invite code (not a
passkey: the passkey is made by the phone or computer the person joins on)
that works as a join link only while the site has nobody, and makes that
person an admin;
from a shell, `flask --app app social invite --base https://...` prints a join
link and `flask --app app social recover HANDLE --base ...` a recovery link
(the way back for an admin who lost every passkey). `.env.example` says how.

**Tables of its own.** `social_people`, `social_passkeys`, `social_invites`,
`social_challenges`, `social_rate_events`: 64-bit keys that never leave the
server, a random public id for every person (`site:` and 26 letters and
digits, what Skribl stores as the author, stable for ever), every index
written with its table, an invite's code kept only as a hash. Their chain is
`social/alembic.ini` (`social/migrations`, stamped in `social_alembic_version`;
Skribl's chain is untouched), run once per start by `gunicorn.conf.py` before
any worker, since Render reads its start command and not the Procfile, and
gunicorn is what both start. A chain that fails is logged and the demo serves
on, the site's sign-in resting (a kind 503) until its tables are there.

**One Skribl, shared.** While somebody is signed in to the site, the Pad and
Flip post as them, and the Gallery names them (name and @handle); while
nobody is, the demo's own identity is asked as before. The site hands both
to Skribl through the seams any host has (`current_user_id`, the author
resolver), composed in app.py, and only where Skribl's CSRF is on.

**Safety, in short.** py_webauthn checks every passkey (discoverable, user
verification required, the sign count stored and checked, a challenge for
one browser used once, the relying party and origin the request's own). The
site's own cookie is signed, HttpOnly, SameSite=Lax, Secure over HTTPS, and
made again at sign-in; every request checks the person's sign-in generation,
which "Sign out everywhere" moves on. Every state-changing request carries
the site's token and its own Origin. Sign-ins, joins and link checks are
limited per address, an invite's tries per invite and an admin's links per
admin, in the database. Deleting an account deletes the person, their
passkeys and their invites.

**Not yet:** the emailed link (an email service, asked first); a list of
signed-in devices; a short undo before an account is deleted (rule 9's undo
window waits for the job queue); and an account's skribls going with it,
which needs a seam Skribl does not have yet (docs/INTEGRATION.md documents
deleting one post by its id, not an author's all): until then the delete
page says the skribls stay, and to delete them in the Library first. The
two follow-ups from its review were made on Nov 11 (the owner's yes): the
limits now write a try first and count it after, so no more than the limit
are ever let through, even at the same instant; and a passkey can be made
and used only at the site's own addresses, once SKRIBL_SOCIAL_HOSTS names
them (unset, each request's own, as before). The move to a domain sets that
list, before anybody makes a passkey at the new name.

`harness/verify_socialauth.py` holds it all through the demo's own server,
with Chromium's own virtual authenticator; DECISIONS.md ("Sign-in at
/social") says what each check was shown red by.

### Built: piece 3, profiles and drawn faces

The owner's "all yes" on the profile mock (A) and "Faces that draw
themselves", built without what does not exist yet: no follower, following or
play counts (follows are phase 2, and counts are kept, never made up), no
comments, no pinned skribl.

| Where | What it is |
|---|---|
| `/social/@<handle>` | **A profile**, any case of the handle: their face, big, in a circle, drawing itself once (Skribl's face player, at 4x or quicker so it takes about four seconds; finished and still under Reduce Motion); their name, @handle and a few lines about them (plain text, 160 characters, 4 lines, nothing invisible or turned around, no links); Share; and their public skribls as Skribl's own Gallery section, newest first, New and Hot and search within them, paging by cursor (since the map's step 4, their tabs in its place: section 16). Your own adds **Edit profile**, **Draw your face** (**Redraw my face** once you have one) and **Settings**, the word with the gear (section 14). Nobody by that name, never made or deleted, is one kind 404. |
| `/social/you/edit` | **Edit profile**: your name and a few lines about you, a form that works without a script, the server's limits said kindly under each field. |
| `/social/you/face` | **Draw your face**: the real Pad over your profile, in its face mode (`?compose=1&face=1`, through `lib/composehost.js`: square, a face's words, no Flip), and "Use this face" sends the drawing here (JSON, the site's token). The site posts it through Skribl's `create_post`, UNLISTED, in the same transaction as your row that names it; a redraw deletes the old one through `delete_post`. |
| `/social/you` | **Settings** now (the gear's): the account page of piece 2, and since section 14 the Theme first. |

**You is your profile.** The bar's You and the rail's foot lead to
`/social/@<handle>` and wear your face, still and small; before you have
drawn one, an empty circle, never a stock silhouette: on your own profile it
says "Draw your face" and opens the Pad, and to anybody else it is empty.
Somebody else's profile marks no place in the bar. A Gallery card shows a
person's face (still) once they have drawn one, and their initial before,
as the card shows any author without a picture; its name links to their
profile everywhere the Gallery is, Skribl's own pages too.

**What Skribl gained, for every host** (docs/INTEGRATION.md, "A face that
draws itself"): the face player (`skribl_face()` and `skribl_face_assets()` in
`skribl/_skribl_face.html`, `face.css`, `lib/face.js`); the Pad's face mode
(`face=1` beside `compose=1`; Flip has none and is unchanged); the in-post
player's draft without its chrome (`chrome=false`); the Gallery section's
`author` and the listing's `visibility=public`; and two keys the Gallery card
reads from the author resolver, `url` (said before, not used by the site) and
`face`.

**Data.** Four nullable columns on `social_people` (`bio`, `face_id`,
`face_w`, `face_h`; migration `fa82723cacc4` on the site's own chain, with its
downgrade). No new index: a profile is found by `handle_key` and an author by
`public_id`, both indexed since piece 2. Deleting an account deletes its face
through `delete_post` and its bio with its row; its other skribls still stay,
as piece 2's confirm says.

**Not yet:** a pinned skribl (it needs a place on the person and a way into
Skribl's Gallery section to show one card first; next); counts; a face
deleted from the Library leaves its circle empty (the site cannot ask Skribl
whether a skribl is still there through a documented seam).

**An empty profile says it in its own words** (the owner's yes, Nov 10): to
its own person, "Nothing here yet. Your skribls show here when you tick Show
in the public gallery as you post, or later in your Library."; to anybody
else, "No skribls here yet." (the Gallery section's `mine`, beside
`author`). Since the map's step 4 each tab says it in its own words
(section 16).

**A face from a skribl you made** (the owner's "all yes" on mock A, Nov 11).
Change my face (Add your face before there is one, and the empty circle)
raises Your face, Make's own sheet, with two doors (three since Trace a
photo, below): Draw a new one (the Pad, as before) and Use one you made. That lists your skribls (yours alone, the
link-only ones too; Pad drawings, never a Flip or the face you have), or opens
a .skribl file you saved, then places it in the circle: drag it (a finger,
the pointer or the arrow keys), size it (the slider or a pinch), and Use this
face. It is kept as a face of its own, through Skribl's `lib/faceframe.js`
(docs/INTEGRATION.md, "A face from a drawing you already have"): a new square
drawing with its own card, posted unlisted as any face is. The drawing it
came from is never changed. A Flip, or a drawing with a picture under it, is
said kindly where it was picked ("not yet"), and the picker stays. Not yet: a
Flip as a face (one that moves), and a face from a drawing with a photo.

**Trace a photo** (the owner's "all yes, build A", Nov 11, after asking
whether a person could upload a photo, or have Skribl draw one from it).
Your face's third door, between the other two: the device's own photo
picker, then the Pad with the photo faint under the canvas (40% to start), a
guide to trace in your own lines. Only the lines are kept: the Pad leaves
the photo out of the face and its card, and the site drops one sent anyway
(profiles.py). In face mode any photo is a guide, which closed the side door
where a photo under a face was kept with it. Why not a photo, or a drawing
made from one: a face that draws itself is the site's signature, a photo of
a teenager's face is the riskiest thing a 13-and-over site can hold, and a
drawing made by a machine would replay a performance nobody gave.
docs/INTEGRATION.md, "A photo to trace".

**A face fits the circle, and Edit this face** (the owner's "all yes", Nov
11, after a traced face did not fit: "there should be a way to adjust the
size so it fits in the circle. also, maybe you should be able to edit it
after it's done"). Whatever the Pad hands back, drawn, traced or edited, goes
to the circle before it is kept: it starts with ALL of the drawing inside
(Skribl's `lib/faceframe.js` fit), and is dragged and sized as a skribl you
made is, then Use this face. Back from the circle is the Pad again, the
drawing still in it, and the photo under it again if it was traced. Once
there is a face, Your face's first door is **Edit this face**: the face back
in the Pad (Keep drawing, then add, undo or erase), then the circle. A drawing
the circle cannot take is kept as it was drawn. The Pad over the page is
`social.js`'s `SocialPadOverlay`, one controller for a face and, next, a post.

**Your face first, drawn in our pen** (the owner's "all yes" on mock C, Nov
11: "do you think those icons represent skribl ... the 4 in a column look
kinda weak"). The face you have leads Your face, the sheet's one big door,
and draws itself again each time the sheet rises (a still under Reduce
Motion); before there is one, the empty circle leads, Draw your face. The
other ways sit side by side under it as tiles. Their icons, and the bar's
Home, are drawn in the signature's
pen (`_icons.html`): faint is what is already there, solid is your new line,
in the small violet ink on the note's tint; each draws itself once as the
sheet rises. Make's sheet joined the family the same day (the owner's "all yes" on its
mock C): Draw and Flip side by side as equals, the Pad and Flip being siblings,
each with its icon in the same pen (your line across a blank page; onion skin,
as Flip shows it), its name, and the line that says what it makes.

**Explore's icon is Blooby holding up a bloob** (the owner, Nov 12: "How
bout a blooby icon? ... You're exploring bloobs, right," then "I do like
g"): his head over a drawing on its card, his hands on its corners, from his
own drawing. Drawn in the bar's colour away from Explore, as Home is; lit
up in his colours on Explore's own page, in either theme (his purple the
wordmark's, `--brand`; his ink, blush and the card's paper `--blooby-ink`,
`--blooby-blush`, `--blooby-paper`). `harness/verify_social.py` section 2
holds both, and his purple at 3:1 or more on the bar.

`harness/verify_socialprofile.py` holds it all through the demo's own
server, faces drawn through the real Pad with a pen; DECISIONS.md ("Profiles
with drawn faces at /social") says what each check was shown red by.

### Built: piece 4, posts

From the approved mocks (Home's composer and feed, "A post", the ⋯ sheet)
and the owner's "all yes" to piece 4's choices (Nov 11). `social/posts.py`:

    /social/              Home, signed in: everyone's posts, newest first
                          (Following came with phase 2; Home's box, "Say
                          something, then draw it…", went on Nov 14: Make is
                          the way to post). Signed out, the first visit.
    /social/posts         a post: the words and the drawing (JSON)
    /social/feed          the next page of the feed, for Load more (JSON)
    /social/p/<id>        a post's own page: its drawing plays by itself
    /social/p/<id>/delete your own post, gone: its words and its drawing (JSON)
    /social/b/<skribl_id> a drawing shown outside a post, on a page of its own;
                          where every gallery card on the site opens
    /social/b/<skribl_id>/delete  your own such drawing, gone (JSON)

**A post is a drawing and words** (the words optional, up to 500
characters). Draw and Flip open Skribl's editor over Home in compose mode;
its Add hands the drawing back, and the composer shows it in the in-post
player, the same player the post will have, with Edit drawing and Remove.
Post sends both: the skribl through `create_post` and the site's row
(`social_posts`, on the site's own chain) in one transaction. The skribl is
unlisted (reachable by its link, listed nowhere but the site); its title is
the post's first words. NO GALLERY TICK since Nov 19 (the walkthrough's
mocks, choice 2, the owner's "all yes"): the composer asked the editors for
"Show in the Skribls gallery" (`?gallery=1`), which fed Skribl's own
gallery, a page the site has no door to, and said "Off, it shows in your
post only" where the site's Gallery shows every post's drawing. The Pad's
sheet still asks "Viewers start at"; the route still keeps a payload that
says public, as the posts made with the tick are. AND THE EDITORS' MENU
INSIDE A POST has no Library and no Public gallery (choice 1): they took the
frame to Skribl's own pages and the drawing on the canvas with it, nothing
asked (docs/INTEGRATION.md, "Nothing in the editor's ⋯ menu leaves your
composer without asking"). A press on Post with nothing said or drawn says so.

**A post can be its words alone** (the owner's "I like your pick", Nov 16, to
A on the words-only mock: "a person should be allowed to post without a
drawing or flip"), as a comment can and a quote of words alone. Post works
once there are words; the post has no drawing and no quote (`skribl_id` is
None, `is_quote` false), and its card is its words and its row, with no empty
drawing box, so it takes little room beside the drawings around it. Its page
is its words and the comments under them. The Gallery, which holds drawings,
never shows it. The database's rule says a post has a drawing, a quote or
words (`ck_social_posts_drawn_quoted_or_said`, revision 7db36bfedef0); going
down past it refuses while a post of words alone is there.

**The feed** reads its drawings' sizes, lines and plays through Skribl's new
`describe_posts` (docs/INTEGRATION.md, "Reading them on your server"), one
query a page, for the person looking; each card is still until tapped. Load
more brings the next page in place, paged by a cursor that names no internal
id.

**A drawing shown outside a post has a page of its own**: one posted from
the Pad on its own page (Make's Draw) and shown in the gallery
(`/social/b/<id>`: its drawing plays by itself, its ⋯ and its Delete, its
author's alone, and since phase 2 its comments, section 10; More from its
author's posts and drawings stood on it until the Calm Post Page, Nov 20,
section 23). From Nov 12 (the owner's "all yes" to A, of Home
saying "No posts yet" while Explore was full) such a drawing was on Home
too, among the posts. Since the map's step 3 Home holds posts only (section
16, decision 2): the drawing stays on its own page and its maker's page
(and on More from until Nov 20, which read it through Skribl's
`list_public_posts`: docs/INTEGRATION.md, "A feed of your own people's
drawings"). A post's
drawing's page is the post's. `harness/verify_socialposts.py` section 9
holds it.

**Every card opens its post** (the owner, Nov 13, from the phone: "Show me
where you click or touch to go to post view? It's not clear. I thought on
card?"; the rule said yes to on Nov 12, "anywhere on the card should open the
post and clicking on the player should make it play"). On Home's cards the
line under the drawing ("Drawn in 16 sec · watching at") and the space around
the drawing open the post too, as the rest of the card did (`posts.js`); the
speed and its choices, the heart, the scrubber and the loop keep their own
taps. Explore's cards, a profile's Skribls and the first visit's newest were
Skribl's own Gallery cards (none is on the site's pages now: Explore's and a
profile's are the site's own tiles since the map's steps 3 and 4, and the
first visit's are the Gallery's six newest since Nov 14), and they open where the site says, through
Skribl's seam for it (`skribl.set_card_url`, docs/INTEGRATION.md "Where a
Gallery card opens"; the demo's `app.py` sets it for the site's own pages):
`/social/b/<id>`, from anywhere on the card that is the card's own, by Home's
rules, with the title a link to it and the ⋯'s Open going there. One address
serves every card: `/social/b/<id>` takes a post's drawing on to its post for
anybody who may see it (and is as gone as the post to anybody else, naming
nothing), and sends a drawing by somebody not on the site, which has no page
here, to Skribl's own page for it. Skribl's own `/gallery` is as it was.
`harness/verify_socialposts.py` section 12 holds it: Cal's tap map as rows,
read since Nov 14 on Skribl's `/gallery` given the address the site's pages
gave (no page of the site holds Skribl's section now).

**A post's own page** plays its drawing by itself, at the author's speed,
sound off until the viewer turns it on, and never under Reduce Motion (the
player's own `play()`: docs/INTEGRATION.md, "A post's own page can start
it"). Its author, its words, when (in the person's own time), its plays,
Share (and Make your own until Nov 14, when it came off: the owner's "Yes,
remove it", as it was the bar's Make by another name, which stays in the bar
and the rail); Comments' place kept ("Comments open soon"; since
phase 2 the comments themselves, section 10); on a desk, the drawing on the
left and More from its author beside it, each tile the drawing alone, cut out
of its share card as Skribl's face macro does (More from went with the Calm
Post Page, Nov 20, section 23; a draw-back's tile is that plate now).

**The ⋯ sheet**, as the mock drew it: Copy link, Share…, and Report this
post (and since piece 5, signed in, Block @them), or on your own Delete
post. Report rises as a sheet of its own (since piece 5 into the site's own
queue, below). Delete asks once and takes the words and the drawing.
Deleting an account takes its posts the same way. Since Nov 14 its rows are
one card, the risky ones a card of their own, with no Cancel ("A list of
choices is one card", at the end).

`harness/verify_socialposts.py` holds it through the demo's own server.

### Built: piece 5, report and block

From the Safety mock and the owner's "all yes" (Nov 12): report anything;
block both ways, quietly. `social/safety.py`:

    /social/report              a report of somebody, a post, or a drawing
                                shown outside a post (JSON), from anybody who
                                can see it, signed in or not
    /social/@<handle>/block     block them (JSON)
    /social/@<handle>/unblock   lift your block (JSON from a sheet; a form
                                from Settings or their profile)

**Report anything.** A profile's ⋯ (beside Share, never on your own) says
Report @them and, signed in, Block @them. A person has their own reasons:
spam or a fake account, abusive or hateful, pretending to be someone, under
13, a child's safety, something else. A post's and a drawing's Report has the
Gallery's reasons and a child's safety, and goes to the site's own queue
(`social_reports`, on the site's chain), no longer Skribl's. A report is a
row, never an action: nothing is hidden because somebody reported it. Who
sent it is kept for the admins' eyes only, and one reporter makes one row for
one thing. Skribl's own report sheet (Explore's tiles, a drawing's link page)
offers a child's safety too, into Skribl's queue, where
`python -m skribl.takedown --reports` lists those first, with a word about the
law (in the US, reporting to NCMEC: the owner's lawyer sets that up).

**Block, both ways and quietly.** From a profile's ⋯ or a post's ⋯, asked
once. While it stands neither sees the other's posts or drawings: Home, a
post's page, a drawing's page. To the one blocked, the blocker's
profile is "Nobody here by that name"; the blocker finds theirs saying so,
with Unblock, and nothing they made. Nobody is told. Settings lists the
people you blocked, newest first, each with Unblock, and only the blocker
lifts a block. Deleting an account takes its blocks; a report naming it
stays, naming nobody.

**A block reaches Skribl's pages** through the two seams Skribl gives every
host for a block list (docs/INTEGRATION.md): a feed filter (the first
visit's gallery's and a profile's Gallery tab's drawings) and a visibility
policy (a drawing's link page, payload and card; the card falls back to its
blank canvas). A host that mounts the site installs both, asking
`social.hidden_authors(viewer_id)` (a block either way, and since the second
part anybody an admin took down, below), as it installs the author resolver;
the demo's `app.py` does.

`harness/verify_socialsafety.py` holds it through the demo's own server.

### Built: piece 5, your Reports, and what taking something down does

The second part of the same "all yes". `social/reports.py`, for the site's
admins alone: anybody else, signed in or not, gets the same 404 as a page
that is not there (Invites' rule).

    /social/reports          the open reports, a card per thing
    /social/reports/down     Take it down (a form)
    /social/reports/keep     Keep it (a form)

**One queue from two.** The site's own reports (somebody, a post, a drawing
shown outside a post) and Skribl's (what people reported on Skribl's own
pages: Explore's tiles, a drawing's link page), read through the two seams
Skribl gives a host for its own reports page, `list_reports` and
`close_reports` (docs/INTEGRATION.md, "Your own reports page"). A post's
drawing reported on Explore lands on the post's card.

**A card per thing,** a child's safety first, then the newest. A child's
safety's card is ringed, its picture and words blurred until Open it; Keep
it and the link to its page come only once it is opened, and it says what
the law may ask (in the US, reporting to NCMEC: the owner's lawyer sets that
up). Every card says what was reported and whose it is, each reason and how
many gave it, what reporters wrote, and who they are ("somebody signed out",
"somebody on Explore"), seen only here. Settings tells an admin how many
wait.

**Keep it** closes the thing's reports, saying who answered and when, and
hides nothing. **Take it down** hides it from everybody else at once and
closes its reports, Skribl's too. Nothing is deleted:

- A post is gone for everybody but its author, as a deleted one is, and its
  drawing is withheld in Skribl (`set_post_visibility(..., "withheld",
  require_author=False)`, the operator's own state).
- A drawing is withheld in Skribl.
- A person's profile is nobody's to everybody else, and all they made is
  hidden, on the site's pages and Skribl's. They can still sign in, see their
  own with the note, and delete their account; nothing new is shared from
  it (posting answers `taken_down`, said kindly in the post box).

Its maker sees "Taken down: it broke the rules. Only you can see it." on a
post or a drawing taken down, and a person taken down sees it on their
profile. `taken_down_at` on `social_people` and `social_posts` holds it (a
migration on the site's chain). The page has no undo yet; since nothing is
deleted, a takedown can be lifted by hand (`taken_down_at` emptied; for a
drawing, `python -m skribl.takedown <id> --visibility public`).

`harness/verify_socialsafety.py` sections 10 to 14 hold it.

### Built: piece 5, the rules

The third part of the same "all yes": three short pages in plain words,
`social/rules.py`, each saying it is a draft that a lawyer reads before the
site opens to everyone, with the mock's pills between them.

    /social/terms     Terms: the mock's own words (your drawings are yours,
                      who can join, be kind, when something is reported)
    /social/privacy   Privacy: what is kept, what is not done, who sees what,
                      and what goes when you leave
    /social/rules     Community rules: one rule, with an example, for each
                      reason a report can give

Anybody can read them, signed in or not. Join and Settings link all three at
their foot. Privacy says only what the code does: a person's row, the two
cookies (`social_session`, `skribl_csrf`), flood limits counted by a keyed
hash and never the address, a report's sender seen by admins alone. Keep it
true when any of those change. What only a lawyer can say (age, a child's
safety and NCMEC, copyright, privacy law, a contact address, the name) is in
`docs/LAWYER-NOTE.md`, written for the owner's lawyer.

`harness/verify_socialsafety.py` sections 15 and 16 hold it. Piece 5 is done.

**What joining agrees to** (the owner's "all yes" to A, Nov 12, a friend's
read of the lawyer note having asked for it): Join says, just above its links
to the rules, "Joining means you agree to the Terms and the Community rules.
Privacy says what we keep." The person's row keeps which Terms
(`terms_version`, `social/rules.py` TERMS_VERSION: the day those words last
changed; move it whenever they change) and when they pressed Join
(`terms_agreed_at`); both are empty for anybody who joined before, who was
never asked. `harness/verify_socialauth.py` section 2 holds the line and the
row, section 15 its words' contrast.

### The name: Blooby, and its wordmark, blooby.

The owner named the site Blooby (Nov 12: "I like the name blooby and I would
go with 'blooby.'"), in place of "Skribl inside for now" below. The site's
own words and page titles say Blooby, and its wordmark at the top of the bar
and of the rail is blooby. (`social/templates/social/_blooby_mark.html`):
written in Skribl's hand at the skribl mark's scale, the word in the site's
purple, the period in Blooby's blush (the owner: "i actually like the blooby
blush period"). Skribl's own pages keep their name and their mark; "Untitled
Skribl" and a drawing's "skribl" are Skribl's words, and stay.
`harness/verify_social.py` section 2 holds the mark: its two colours read off
each stroke, the word at 3:1 or more, and the line where the old mark's was.

### The move to blooby.app

The owner bought blooby.app (Nov 11; on Cloudflare) and said "all yes" to:
blooby.app opens the site's Home, its pages at /social/... for now; the
name "Skribl" inside for now; Cloudflare's proxy off (DNS only), so Render
makes the HTTPS certificate and the rate limits' one proxy hop stays one.

What the app does: the top of an address `SKRIBL_SOCIAL_HOME_HOSTS` names
goes to the site's Home (302: "for now"); every other address keeps the
demo's own top, the Pad. `harness/verify_social.py` section 1 holds both.

What the owner sets up, once:

1. Render, the service's Settings, Custom Domains: add `blooby.app`. Render
   shows the DNS records it wants and makes the certificate once they answer.
2. Cloudflare, DNS: add exactly those records, each with the proxy OFF (the
   grey cloud, "DNS only").
3. Render, Environment: `SKRIBL_SOCIAL_HOSTS=blooby.app,skribl-live-demo.onrender.com`
   and `SKRIBL_SOCIAL_HOME_HOSTS=blooby.app`, then let it deploy.

Moving people: a passkey belongs to the address it was made at, so each
person adds one at blooby.app with a recovery link. On the old address, an
admin opens Invites and makes a recovery link for the person (themselves
first); the link is opened with `blooby.app` in place of the old address
(`https://blooby.app/social/recover#...`), which adds a passkey there.
From a shell instead: `flask --app app social recover HANDLE --base
https://blooby.app`. The old address keeps working meanwhile.

## 10. Built: phase 2, comments

From the comments mock and the owner's "all yes on both" (Nov 12), in the
mock's own classes, sizes and words. `social/comments.py`:

    /social/p/<id>/comments           POST: a comment on a post, or a reply
                                      to one at any depth (JSON); GET: the
                                      next page of its comments, for Load more
    /social/b/<skribl_id>/comments    the same, on a drawing shown outside a
                                      post (below)
    /social/c/<id>                    a comment's or a reply's own page (the
                                      comment thread, section 18): the way to
                                      it, it as big as a post, its replies
    /social/c/<id>/delete             your own comment, gone; or, on your own
                                      post or drawing, anybody's, removed from
                                      it; one with replies under it keeps its
                                      place, so they stay (JSON)

**The comment thread, step 1 (section 18, the owner's yes, Nov 17), changed
what this section first built**: every comment sits in a bubble with its row
under it (Reply and ⋯, the ⋯ "This comment": Copy link, Share…, then Delete
comment, or Remove from my post and Report this comment); "Reply" is the word
wherever the site said "Answer"; a reply keeps the reply it answers, and
every list shows one level, the direct replies to what its page is about,
each with "Read N replies" to its own page, which a tap on it opens too. A
comment or reply deleted while replies hang under it keeps its
place, quietly ("This comment was deleted", or "removed" from the post by
its author), so they stay where they are; with nothing left under it, the
place goes too. Where this section says "answer" below, read "reply"; where
it says deleting a comment takes its answers, read the place; section 18
says what the thread is now.

**On a post's own page** "Comments" and how many stand where "Comments open
soon" was, and **the comment box is an icon** at the heading's end (the owner,
Nov 13: "The comment needs to be an icon not a card. It takes up too much room
sitting there"): a round lilac button, a bubble with a plus, "Say something".
The box is Home's composer in the mock's size (your face, "Say something, or
draw it…", Draw and Flip, and Post), folded away until asked for. On a phone
it rises on Make's own sheet, "Say something to Mira", its field ready; on a
desk it glides open under the heading, the icon lit. Put away (the dimmed
page, a drag down or Esc on a phone; a second click, Esc or a press elsewhere
on a desk), it keeps what was typed for as long as the page is open. With no
comments yet, "Say the first thing" stands where they will be and opens it
too. (SINCE THE CALM POST PAGE, Nov 20, section 23: no heading, no icon and
no "Say the first thing". The answer bar's one line, "Say something…",
opens the box, and on a desk the box opens in that line's place.) The comments come newest first, each with its face, name, a short time
("40m", "2h"), its words or its drawing, Answer and ⋯; twenty a page, then
Load more. **Answers sit one level under a comment, oldest first**:
answering an answer puts the new one under the same comment. Answer opens
the same box for it: on a phone the sheet is titled "Answer Theo", Theo's
words in a line under it; on a desk it glides open under that conversation
("Answer Theo…"), and if that is below what the screen shows the page glides
down to it. Answer again, Esc or Post puts it away. Posted, the box goes as
the comment comes (on a desk in step), and the comment glows a moment in
Activity's landing tint. On a desk the comments sit beside the drawing, under
Share. Home's card says how many beside the plays ("3 comments", a way to
them), and at none its icon alone, named "Comment" (below).

**On every drawing** (the owner's yes, Nov 12: "Comments on every drawing,
however it was made, so whatever you open has the comment box"). A drawing
shown outside a post, made in the Pad or Flip on their own pages and shown in
the gallery, has the same comments on its own page (`/social/b/<id>`): the
box, answers, drawing answers, the ⋯ (its maker removes, as a post's author
does), reports, Load more, the count in the row under it (on Home's card
until the map's step 3). They follow its page, which decides who may see it
(public, its maker one of the site's people, no block either way, nothing
taken down but to its maker: `posts.bloob`, one rule for the page and its
comments). A block either way with its maker, the drawing taken down
(withheld) or its maker taken down, and the drawing deleted in the Library:
its page is gone to them, and so are its comments, read, said, answered or
reported. Its maker still sees them on a drawing taken down, with the note,
and no box. Deleted through the site (its ⋯, Delete), it takes its comments
with it, in code, and their drawing answers.

**Easier to open a post** (the same yes: "tap its words, its name line or its
time; the 💬 shows even at zero"). On Home's cards the words and the time are
each a link to the card's own page (a post's; a drawing's too until the
map's step 3); the face, the
name and the @handle still go to the person's page, as everywhere else on the
site (the owner was told: "its name line" kept going to the profile). The 💬
shows even at none: its icon alone, named "Comment", a 44px way to the
comments. Nothing on the card moved: the name's link lies under the @handle
too, so the person's link is the whole name line's 44px as before, and the
time's link, over it, is 44px by reaching down into the room under its line
(toward the words, which go where it goes; on a card with no words the
drawing lies over its last 11px or so and keeps its taps there, so the
time's own tap is 33px tall, the card's ground around it opening the post
too). More from's tiles were whole links already; a profile showed Skribl's
Gallery, not these cards, until the map's step 4 put these cards on its
Posts and Likes.

**Anywhere on a card opens its post** (the owner's addition, the same day,
a plain yes). A tap or a click on a card's own ground opens its page, as its
words and its time do; they stay its real links, for a keyboard and a screen
reader, and the card is not one big link (`posts.js`, a tap on the card's
ground: one that did not land on anything with a job of its own). What has
its own job keeps it: the drawing plays and pauses and never opens the post
(its player stops its own taps, and is set apart besides); the face, the
name and the @handle open the person's page; ⋯ and Share their own sheets;
the 💬 the comments. A press that moved is a drag, and a click that ends a
text selection opens nothing, a link's included; the words select when
pressed and pulled (`draggable="false"` and `user-select: text`, which
Chromium needs to select inside a link at all). Ctrl or ⌘, or the middle
button, opens a new tab. On a desk the card shows a pointer; nothing on a
phone changes.

**Who may comment:** somebody signed in, not taken down, with no block
either way with the author of the post or the drawing; an answer also with
none with the author of the comment it answers, and on what that comment is
on. The route refuses anybody else kindly, and neither the box nor the line
that opens it (its icon until Nov 20) is shown to them. Signed out, the
comments are readable and the line raises
"Say something?", whose Sign in comes back to the page with the box open
(nothing is posted until Post). The
words are a post's: tidied, 500 characters at most, nothing hidden or turned
around; 60 comments an hour a person (`comment` in security.LIMITS). A
comment needs words or a drawing.

**A drawing answer** (the second part; the mock's 6. "Reply with a skribl",
phase 3's, came early with the owner's yes to this mock.) Draw and Flip in
the box (on a phone's sheet as in place) open Skribl's editor over the post
in compose mode (`?compose=1`, no
gallery tick; `lib/composehost.js` through `SocialPadOverlay`, as Home's
composer). Add hands the drawing back, and it waits in the box, in the
in-post player the comment will have, with Edit drawing and Remove, until
Post. It is posted through Skribl's `create_post` in the same transaction as
the comment that keeps its id, UNLISTED whatever the payload says (its link
works, it is listed nowhere), titled by the comment's first words; a comment
needs words or a drawing. On the page it is Skribl's in-post player, 150px
wide in the drawing's own shape with the player's line under it, still and
not even fetched until tapped: the post's own drawing alone plays by itself.
It goes with its comment, its post and its person's account (Skribl's
`delete_post`, as its author), is withheld with its comment when an admin
takes it down, and what is reported of it on Skribl's own link page lands on
its comment's card. A post's own page loads `lib/composehost.js` only for
somebody who may comment; so does a drawing's.

**What is shown, and counted:** nothing by anybody hidden from the viewer (a
block either way, or taken down), nor the answers under it, on the page and
on Home's card alike. A comment's ⋯: your own is "Your comment", Delete
comment; somebody else's on your own post or drawing "Theo’s comment",
Remove from my post and Report comment; anybody else's Report comment.
Delete and Remove go at once (the ⋯ is the asking), the comment fading out
with its answers. Report sends a post's reasons into the site's own queue
(kind `comment`); Your Reports shows its card (whose, its words, a link to it
on its post's or its drawing's page), and Take it down hides it from
everybody but its author, who sees "Taken down: it broke the rules. Only you
can see it."

**Data.** `social_comments`, on the site's own chain (migration
`e4b8c2a91f37`): `public_id`, `post_id`, `person_id`, `parent_id` (always a
top-level comment's), `words`, `skribl_id` (a drawing answer's), `created_at`,
`taken_down_at`; indexed by address, a post's newest first, a comment's
answers oldest first, a person's, and a drawing answer's. Since comments on
every drawing (migration `ded60afbc86d`), a comment is on a post (`post_id`,
nullable now) or on a drawing shown outside a post (`drawing_id`, the
skribl's own public id: the site has no row of its own for it), exactly one
(`ck_social_comments_on_one`); an answer is on what its comment is on.
`owner_id` is whose the post or the drawing is (filled from each post's
author for the comments already there), so deleting an account and a block
never ask Skribl whose a drawing was; indexed too, as are a drawing's
comments newest first. Deleting a comment takes it (a place stays while
somebody's replies hang under it: step 1, above), a post or a drawing its
comments, an account its comments (each a place while somebody else's
replies hang under it) and every comment on what it owned: said in code
(`comments.retire`, `posts.drop_post`, `posts.bloob_delete`,
`accounts.delete_person`), never
left to the schema's ON DELETE CASCADE, which SQLite enforces only where
Skribl's pragma hook is on. A drawing deleted in the Library (Skribl's own
page, outside the site) takes its page, and so its comments, from everybody
at once; their rows stay until its maker's account goes, or each commenter's,
since Skribl tells a host nothing when a drawing is deleted on its own pages.
The chain taken back down deletes the comments on drawings (there is no post
for them to be on).

**Counted, not kept (for now).** Section 3's rule 3 keeps counts as stored
numbers. A comment count that hides what a block hides is each viewer's own,
so it is counted, by the page's own rules, one read a page for each kind
(posts', drawings'); a kept count waits for a measurement that asks for it.
Since the comment thread (section 18) that read is recursive, from the
comments down, each step on the reply's own index, so a reply under one
hidden from the viewer is not counted at any depth.

`harness/verify_socialcomments.py` holds it through the demo's own server
(sections 20 to 28 the drawings'), and `harness/verify_socialposts.py`
sections 10 and 11 the card's ways in; DECISIONS.md ("Comments at /social", and
"Comments on every drawing") says what each check was shown red by.

## 11. Built: notifications

Since the comment thread (section 18), Activity says "replied to your
comment" and "replied with a drawing" where this section says "answered",
and a row's link lands where the comment shows: a comment on its post's or
drawing's page, a reply on the page of what it answers.

From the notifications mock and the owner's "all yes" (Nov 12), A, in the
mock's own classes, sizes and words. `social/activity.py`:

    /social/activity    who said something on your posts, and who answered
                        you: New, then Earlier, a row each; opening it marks
                        everything seen

**Where it lives.** Signed in, a bell drawn in our pen stands at the top right
of a phone's Home and Explore, where "Sign in" sits before you sign in (44px,
named "Activity"); on a desk, Activity is in the rail after Explore, on every
page, its bell filled and the pen's line under its name on its own page. The
bar keeps its four places: Activity is not in it, and on Activity's own page
a phone's top says "Activity" with the way back, as a post's says "Post". The
bell has a dot when something is new since you last looked, and the dot goes
once you look: a tap on the bell lets it fade as Activity opens, and on a
desk's Activity page the rail's fades once the page is there.

**The dot's colour** is a new token for a new job, `--new-dot`: Blooby's
blush a shade deeper on light (`#e64a78`, 3.64:1 on the page, where his own
blush reads 2.58:1, under the 3:1 a mark needs), his blush itself on dark
(`--blooby-blush`, 7.34:1). It is ringed in the page's own ground, so it
stands clear of the bell's line, and each new row in the list wears it too.

**A row** is a comment or an answer, not yours: answering you ("Theo answered
your comment", or with a drawing, "Juno answered with a drawing"), or else on
what you own, a post or a drawing shown outside a post ("Mira said something
on your post", or with a drawing, "Juno commented with a drawing"). Their
face, who and what, when as comments say it ("5m", "2h"), their words under it
in quotes (two lines at most), and the small picture: the drawing they
answered with or drew, else the post's (or the drawing's), cut from its poster
as a draw-back's tile is. Each row is one link to that comment on its page
(`#c-<id>`, a post's or a drawing's).

**Grouped since you last looked.** Several comments on one post since you
last looked are one row, the newest face in front and the next behind, the
newest words under it, and the row opens the newest: "Mira and 2 others said
something on your post" ("Mira and Theo" for two). Answers to you in one
conversation are one row the same way. A drawing keeps a row of its own, so
its picture shows. Earlier keeps a row for each comment, as it was said (the
mock's pictures show the cottage's two comments as two rows).

**Seen is opening Activity.** The page reads the list, then keeps the time it
was opened on your row; the rows that were new keep their dot while you are
there, and next time they sit under Earlier. Nothing to tick or clear.

**Never in it:** yourself; anybody hidden from you (a block either way, or
taken down); a comment taken down, or an answer under a comment you are not
shown; anything on a post or a drawing whose page you cannot see (a block
either way with its maker, it or its maker taken down, a drawing deleted in
the Library or no longer public). A comment deleted or removed takes its row
with it. These are the rules a comment's own page reads (`comments.seen`),
read for many comments at once, so a row always lands on a comment that is
there. The bell's dot reads the same rules, so it never promises a row the
list will not show.

**Landing.** The comment glows a moment in the note's tint, the comment alone
and not the answers under it, then the tint fades over a second and a half
(`comments.js`); nothing moves, so Reduce Motion keeps the fade. One on a
later page of comments is brought in with Load more, a page at a time, and
the page glides to it (under Reduce Motion it is put there). A drawing answer
opened this way draws itself once, sound off, as a post's drawing starts on
its own page, and the post's own waits: the player plays one at a time.
Landing at words, the post's own plays as on any visit. Under Reduce Motion
nothing plays.

**Nothing yet:** Blooby as his Home Screen icon in small, "Nothing new yet",
"When someone says something on your post, or answers you, you’ll see it
here.", and "Make a skribl", which opens Make's sheet, as the first visit's
button of the same name does.

**Data.** Worked out from the comments, not kept: there is no table of
notifications to keep in step, so a comment deleted, removed or hidden takes
its row with it at once and nothing is ever swept. Two things are kept, on the
site's chain (migration `c276c1445bc1`): `social_people.activity_seen_at`,
when the person last looked (nothing until then: everything is new), and
`social_comments.to_person_id`, whom an answer answers, the author of the
comment or answer whose Answer was pressed. `parent_id` cannot say it: an
answer to an answer sits under the same top-level comment, whoever wrote that,
so without it "answered your comment" would miss every answer to an answer.
Answers already there were filled from the comment they sit under. It is set
to nothing, in code, when that person's account goes (`accounts.delete_person`;
ON DELETE SET NULL is the net). Indexed newest first by whose
(`owner_id, created_at`, which takes the place of the owner's own index) and
by whom (`to_person_id, created_at`): the dot is two searches, one on each,
since you last looked, a handful of rows at most, and Skribl is asked only
when every new one is on a drawing (whether its page is still there). It is
asked once a request, by a page with the bell or the rail. The page reads the
newest 100 comments.

`harness/verify_socialactivity.py` holds it through the demo's own server;
DECISIONS.md ("Activity at /social") says what each check was shown red by.

## 12. Built: likes

From the likes mock and the owner's "I like d." (Nov 13), then "All yes, b":
everyone sees how many, and who liked it is only ever the maker's to see.
`social/likes.py`:

    /social/p/<id>/like             POST {liked, at_ms}: your like on a post,
                                    given or taken back
    /social/b/<skribl_id>/like      the same, on a drawing shown outside a post

**Since Nov 13 the heart is in the row under the drawing** (section 16,
step 2: after the comments, before Share and the ⋯), and Skribl's line has no
lead any more; what follows is the heart as it was first built.

**The heart.** Drawn in our pen, one line round from the notch at the top (the
mock's own path), in a pill at the start of the line under the drawing (the
owner's way 3, "Yes", after "I don't even see the heart to like on many
pages"): on Home's cards, a post's page and a drawing's own page
(`/social/b/<id>`) alike. It is that line's lead, Skribl's general seam for
one control of a host's (docs/INTEGRATION.md, "A control at the line's
start"), so Skribl dresses it as the loop button at the line's other end:
32px tall, its lilac ground and the line's ink, its hover and focus ring, a
44px tap area from the drawing's edge to 2px under the pill, clear of the
speed's. The scrubber gives it the room (59px with one figure) and nothing
else moves: a card's foot (plays, comments, Share) and a page's
time-and-plays line are as they were. `aria-pressed`, named "Like" or "Liked",
with how many. It stays empty, just its line in the line's ink, until *you*
like it, whatever the number beside it says. The heart and its count are one
part (`_post.html`, `heart()`, and one block of `social.css`, "LIKES"), so its
place can change in one go. Being on the line, it shows when the line does,
and while a drawing can't be shown the line steps away with it.

**Liking.** A tap draws the line round in blush from the notch (about a third
of a second), the blush fills in behind it and the grey line fades under it;
nothing grows, bounces or moves. The same tap takes it back: the blush and its
line fade and the grey line comes back, nothing un-drawing. Under Reduce
Motion it only fades. A count that comes fades in as the pill grows round it,
the scrubber giving up its room as it does and the heart never moving; one
that goes fades first, then the pill closes round the heart (nothing glides
under Reduce Motion). The page changes at once and tells the site; one
request at a time a heart, so quick taps end where the last one left them,
and if the site says no, the heart goes back and the page says why, kindly.

**The liked heart's line** is a new token for a new job, `--heart`, with the
dot's values (`#e64a78` on light, 3.74:1 on a card where Blooby's blush would
read 2.65:1; his blush itself on dark, 6.01:1), his blush inside it; Activity's
small heart wears it. ON THE PILL'S LILAC the line is a step deeper on light,
`--heart-line` (`#d11a32`, the dots' third step: 4.28:1 on a card's pill and
4.17:1 on a page's, where `--heart` would read 2.97:1), his blush itself on
dark (4.89:1 and 6.18:1). The empty heart's line and the count are the line's
ink: 14.27:1 and 13.93:1 on light, 11.43:1 and 14.44:1 on dark.

**How many** is everyone's, in the pill beside the heart, with no number at
zero (just the heart, a 32px circle), counted by the viewer as comment counts
are: a like by anybody hidden from them (a block either way, or taken down) is
neither shown nor counted, anywhere. Home asks once for all its cards (one
grouped read a kind, posts and drawings). One like a person a thing; you may
like your own.

**Who may like:** somebody signed in, not taken down, on a post or a drawing
open to them (the comments' rules, through the same `comments.On`: there for
everybody, no block either way with its maker). Every like shows the site's
token and Origin and is limited a person (120 an hour, likes and taking back
alike). Signed out, the heart is there all the same, and a tap raises a small
sheet: "Like this drawing?", "Sign in, and a tap on the heart lets Mira know
you like it.", Not now and Sign in, which comes back to the same page, where
the heart waits: nothing is pressed for them.

**Each like keeps its moment.** Tapped while the drawing plays, a like keeps
where its replay was, in ms on the drawing's own clock (so the same moment
whether it was watched at ¼× or 16×), read from Skribl's in-post player
through its playhead seam (docs/INTEGRATION.md, "Where the playhead is");
tapped while it is still or paused, no moment, and it counts all the same.
The site keeps only a whole number of ms from 0 to a day.

**The dots on the line** (part 2; the owner's "Just put a smaller dot (same
color as blooby blush) wherever someone likes it. If it doubles someone it
gets redder.", then "All yes, b"). Every like with a moment is a small dot
(5px, phone and desk alike) over the line under the drawing, in the middle of
the gap between the drawing and the scrubber, where *the line itself* puts that
moment: the playhead's own place for it, so a piece played with its long
pauses squeezed lines up as its playhead does, and a Flip's pages each take
their share. Likes that land so close their dots would overlap are one dot of
the same size, a step redder: two together, then three or more, never bigger
and never a number (a desk's longer line can keep apart what a phone's
doubles). On Home's cards and a post's or a drawing's page alike, from the
same grouped read as the count (one for Home's whole page, which holds posts
only), counted by
the viewer in the same way: a like with no moment has no dot, and nobody
hidden from the viewer (a block either way, or taken down) has one. Dots say
where, never who: the page is sent each moment and how many, nothing else.
Your own like moves your dot with your heart: liked while it plays, a dot
fades in where you tapped; taken back, it fades out. Nothing taken down has
dots. They take no taps: a finger on one lands on the scrubber under it. The
colours are (b), the bell dot's pairing: on light `--heart` (`#e64a78`, the
sheet's dot: same role, same token), then `--heart-2` (`#e33157`) and
`--heart-3` (`#d11a32`); on dark his blush, then `#ff4d78` and `#ff2d5f`;
each 3:1 or more on what is painted behind it (on light 3.64:1, 4.22:1 and
5.24:1 on the page, 3.74:1, 4.34:1 and 5.38:1 on a card; on dark 7.34:1,
6.09:1 and 5.36:1, and 6.01:1, 4.99:1 and 4.39:1). Skribl's player draws
them through its marks seam (docs/INTEGRATION.md, "Marks on the line"); the
site gives the moments and the colours (`--mark`, `--mark-2`, `--mark-3` on
`.post-art`), and never names a part of Skribl's.

**The hearts that rise.** As the replay reaches a dot in normal play (the
player says so: `skribl:mark`), a small heart rises from it about 30px and
fades, gone in a second: it fades in as it starts and never pops, never
grows, and the dot stays. It is the liked heart, 14px, its line the deeper
blush in both themes (`--heart-paper`, `#e64a78`), because the paper it
crosses is the drawing's own, the same in both (3.35:1 on the cream paper,
3.64:1 and 5.20:1 on the page where it starts). A redder dot sends one heart.
Scrubbing, a seek or a jump sends none (the player's rule: only frames of
normal play tell, counted from where play starts; a loop coming round tells
again). CALM AT EVERY SPEED: at most three hearts in the air, each at least a
third of a second after the one before; a dot reached meanwhile sends none,
and nothing waits, so no heart rises late from a dot the playhead has left.
Under Reduce Motion nothing rises: the dot glows a moment (a soft halo of its
own colour fading in and out) and nothing moves. Hearts take no taps: a tap
on the drawing where one is rising pauses it, as ever.

**"Liked by…", the maker's alone.** On their own post's or drawing's page,
under the time-and-plays line: the newest three faces and "Liked by Mira, Ada
and 3 others" (all the names up to three), newest first: the others, never
the maker (the owner's A, Nov 14, "It's not really necessary to say liked by
you because the filled heart" does; until then "you" came first when one was
theirs), and when the maker is the only one, no line at all. It opens the
sheet of who, Make's own sheet in its paper with
the people on one card: each one's face, name, @handle and when, and under
when the moment their heart landed ("0:06") where one was kept, newest first,
each a way to their page, the maker's own among them, and "Only you can see
who liked it." Nobody else is sent any of it. The maker's own like, given or
taken back, brings the rows up to date at once; the line comes or goes only
when somebody else's like came or went meanwhile, its room opening or
closing.

**In Activity** a like is a row like a comment's, its face wearing a small
liked heart: "Mira liked your post", when, and the post's small picture.
Several since you last looked on one post are one row, the newest face in
front ("Mira and 4 others liked your post"); a like says no words, so under
Earlier likes stay one row a post as well. A like row opens the post at
"Liked by…" (`#liked`), which glows a moment in the note's tint and fades, as
a landed comment does; with no line there (the other like gone since, its
maker the only one), it lands on the post's heart. **Likes never light the bell's dot:** a like needs no
answer, so it waits under New, with its own dot. You never see yourself;
nobody hidden is in a row. Activity's line says "Who liked your posts or said
something on them, and who answered you.", and with nothing yet, "When
someone likes your post, says something on it, or answers you, you’ll see it
here."

**Deleting is real, and said in code:** a post goes with its likes
(`posts.drop_post`), a drawing deleted through the site with its likes
(`posts.bloob_delete`), an account with its own likes and every like on what
it made (`accounts.delete_person`). The ON DELETE CASCADEs are the net. The
Privacy page and docs/LAWYER-NOTE.md say likes are kept: who liked what,
when, and where in the replay.

**Data.** One table on the site's chain (migration `a81c5c4dde3a`, after
`c276c1445bc1`), `social_likes`, shaped as `social_comments` is: on a post
(`post_id`) or a drawing (`drawing_id`, its skribl's public id), exactly one
(`ck_social_likes_on_one`); `owner_id` (whose it is), `person_id` (who),
`at_ms` (the moment, or nothing) and `created_at`. Unique on (person, post)
and on (person, drawing); indexed by the thing and when (a thing's count, and
who liked it, newest first) and by whose and when (Activity, since you last
looked and before, each one search).

**Pad and Flip:** the seams are shared. `player.playhead()` is one read-only
method on the in-post player that plays Pad drawings and Flips alike, so a
like on a Flip keeps its moment the same way; the line's lead is one slot in
that player's line, which a Flip's post wears as a drawing's does, so the
heart sits on both the same; and the line's marks are that player's too, so a
Flip's likes are dots on its line and send up hearts as a drawing's do (a
Flip's dots wait for its pages, which say where its moments are and come
with the drawing on the first tap). Nothing changes in either editor.

`harness/verify_sociallikes.py` holds it through the demo's own server;
`verify_inline.py` and `verify_seam.py` hold the seams. DECISIONS.md ("Likes
at /social", parts 1 and 2) says what each check was shown red by.

## 13. Built: follows

From the follow mock and the owner's "Yes to all" (Nov 13): B, yours alone.
Who follows whom is only ever the person's own to see; nobody has a count on
show. `social/follows.py`:

    /social/@<handle>/follow    POST {following}: follow them, or stop (a yes
                                or a no, never "toggle")
    /social/home/show           POST {show}: what Home opens on, "following"
                                or "everyone", kept for the account

**The button.** First in the row on somebody's page, before Share and ⋯ (on a
desk the same row, beside their face): Follow, the action's purple with a
plus drawn in our pen, 44px. A tap makes it Following at once, the quiet
button, its check drawing itself in the pen; nothing moves, the purple fades
and the words cross over, and under Reduce Motion it only fades. Both words
sit in one place inside it (one grid cell), so it is as wide as "Following" in
any font and Share and ⋯ never move. It is named "Follow Theo Lind", then
"Following Theo Lind", and says so to a screen reader. Never on your own
page, nor on somebody you blocked (Unblock is there), and never on a card:
the name on a card already opens the person's page. No "Follow back", no
"Follows you".

**Unfollowing asks once.** A tap on Following raises a small sheet, Make's
own: "Unfollow Theo?", "You'll still see Theo's posts under Everyone.
They aren't told.", Keep following beside Unfollow, the big button, the
focus on Keep following. Nobody is told either way.

**Yours alone.** On somebody else's page there is only Follow or Following:
no line, no count, no list, not in the page and not in its source. Your own
page says who under its buttons, the twin of "Liked by…": "Followed by Mira,
Theo and 2 others" with their drawn faces (every name up to three, else two
and how many more, newest first), or before anybody follows you "You follow
Mira and Juno"; with nobody either way there is no line, so nothing ever says
zero. The line opens Make's own sheet in its paper with the one pill,
Followers | Following, each list newest first with when (in your own time),
the people on one card, each a way to their page, and
"Only you can see who follows you, and who you follow." Each row wears the
Follow button their page wears (the owner's "A", Nov 15): Following on whom
you follow, a tap asking "Unfollow Theo?" over the lists, and the row staying
with Follow on it, so a slip is one tap back; Follow on a follower you don't
follow back. The when sits after the @handle; your page's counts change with
the tap, your own, never theirs. Both lists sit in one
place in the sheet, so it keeps its height as the pill moves between them. It
lists the newest 200 of each; the line's count is exact. Opened at
`#followers` or `#following` (a follow row in Activity), the sheet rises on
that list.

**Counted by the viewer**, as likes are: anybody hidden from you (a block
either way, or taken down) is in no line, no count and no list, and in
nobody's Following.

**Who may follow:** somebody signed in and not taken down, anybody else who
is there for them (not taken down, no block either way), never themselves;
the token and Origin first, then the limit (60 an hour, follows and unfollows
alike). A refusal in the page puts the button back and says why, kindly.
Signed out, Follow is there all the same, and a tap raises the small sheet the
heart uses: "Follow Theo?", "Sign in, and Theo's new posts show first on
your Home.", Not now and Sign in, which comes back to the same page, where
Follow waits: nothing is pressed for them.

**Home's pill, Following | Everyone**, under the composer, the Gallery's New /
Hot value for value (the same control, the same glide; the site names its own
tokens for the Gallery's values, `--pill-on-fill`, `--pill-on-ink` and
`--pill-off-ink`). Home opens on Following once you follow somebody, on
Everyone before that, and on your own pick once you make one: a tap keeps it
for the account (`social_people.home_feed`), so it holds on every device. The
switch: the pill glides, the posts fade, change while they can't be seen, and
fade back; the page doesn't scroll. Under Reduce Motion the pill is put there
and the posts only fade.

**Following never runs out.** It is the people you follow and you, their
posts (posts only, as all of Home since the map's step 3; until then their
drawings shown outside a post too, through Skribl's listing's `authors`:
docs/INTEGRATION.md), newest first, nothing ranked. After the last of them,
"You're caught up with the people you follow." with a small check in the pen,
then Fresh from everyone: everybody else's, so nothing shows twice. Load more
carries on through both (a cursor of Following's own says which part it is
in). Somebody who follows nobody and is on Following gets a kind card, "You're
not following anyone yet", how, and Look around (Explore), then everyone's.

**In Activity** a follow is a row like a like's, its face wearing a small
Follow (the action's purple, a white plus in the pen), and no picture: "Mira
followed you"; several since you last looked one row, the newest face in
front ("Mira and 2 others followed you", "Mira and Theo followed you"). One
person opens their page; several open who follows you. Under Earlier a day's
follows stay one row: those within a day of the newest of them (the site
keeps no time zone of yours, so a day is 24 hours, not a date). **Follows
never light the bell's dot:** a follow needs no answer. **Following again
never tells them twice:** an unfollow keeps the row with the time it ended,
so following again keeps the first time, and Activity, which reads it, has
nothing new to say; a follow taken back has no row. Activity's line says "Who
followed you, liked your posts or said something on them, and who answered
you.", and with nothing yet, "When someone follows you, likes your post, says
something on it, or answers you, you'll see it here."

**Blocks:** a block ends a follow both ways, and for good (the rows go), and
none can begin while it stands; lifting the block brings none back. Somebody
taken down drops out of every list and every Following.

**Deleting is real, and said in code:** an account goes with its follows both
ways (`accounts.delete_person`, through `follows.drop_person_follows`); the ON
DELETE CASCADEs are the net. The Privacy page and docs/LAWYER-NOTE.md say
follows are kept: who you follow and since when, and that you once did after
an unfollow.

**Data.** One table on the site's chain (migration `1757a4385be8`, after
`a81c5c4dde3a`), `social_follows`: `follower_id`, `followed_id` (both to
`social_people`, ON DELETE CASCADE), `created_at` (when they first followed),
`ended_at` (when they unfollowed, or nothing while they follow); unique on the
pair, never yourself (`ck_social_follows_not_self`); indexed both ways newest
first, by `(follower_id, created_at)` and `(followed_id, created_at)`. And
`social_people.home_feed`, Home's pick. Home's Following is one read of posts
(the people you follow as a subquery, on the posts' own person index: SQLite
plans it as a MULTI-INDEX OR), as Everyone's page reads them, with no read a
card (and until the map's step 3 one of drawings).

**Pad and Flip:** nothing changes in either editor. Home's cards play Pad
drawings and Flips in the one player they share, so Following shows both
alike; the one change on Skribl's side is the listing's general `authors`,
which any host may use for a feed of the people somebody follows.

`harness/verify_socialfollow.py` holds it through the demo's own server;
`verify_createpost.py` holds the listing's `authors`. DECISIONS.md
("Following at /social") says what each check was shown red by.

## 14. Built: Settings and the theme

From the Settings mock and the owner's "Yes to all" (Nov 13), asked after
"where is the theme picker and other settings?": one choice for Blooby, the
Pad and Flip, and Settings easier to find.

**The Theme row, first on Settings** (`/social/you`), its own small card
(86px, so Your passkeys sits 102px lower): the Pad's own settings row, in its
words and order, **Theme**, then **System**, **Dark**, **Light**, System
keeping the Pad's tip, "Follow the device's appearance setting", and "For
Blooby, Pad and Flip" under the row's name, so the one-choice part is said
once, where it matters. The switch is the Pad's: 216 x 52, three 44px
choices in equal thirds, 15px words at one weight, the one pill sliding under
the choice in the Pad's 0.26s. Its track is the second button's dress (the
site's control on a card); the pill and its inks are the site's one pill
(`--pill-on-fill`, `--pill-on-ink`, `--pill-off-ink`, the Gallery's values, as
Home's pill wears them). Nothing is pressed in the page as sent: the choice
lives in the browser, and `you.js` presses it as the page starts, the pill
fading in where it belongs (never sliding in).

**One choice, Skribl's own.** Blooby, the Pad and Flip live at one address, so
they keep one choice: Skribl's, under `skribl_theme_v1`. The site reads and
sets it only through Skribl's own theme code, the documented seam
(docs/INTEGRATION.md, "Skribl's theme on your pages"): every page includes
Skribl's head boot (`skribl/_skribl_theme_boot.html`, inline in `<head>`,
before the first paint, by the page's own nonce, the one inline script the
site's policy allows) and loads `lib/theme.js`; the row calls
`SkriblTheme.set()`. Pick Dark on Settings and the Pad opens dark, its switch
saying Dark; pick Light in the Pad's menu and Blooby is light when you come
back, its row saying Light. Another tab follows, and so does a page the back
button brings back whole (`social.js`, on `pageshow`). Skribl knows nothing
about the site. The one change in Skribl, for every host: **the boot says dark
out loud** (`data-theme="dark"`), where dark used to be the attribute left
off, so `social.css` can tell light, dark and nothing stamped apart. Light
chosen is the light ramp; dark chosen is the dark ramp; nothing stamped (no
script ran) follows the device, so the dark ramp is written twice, once for
each way to dark, and `verify_socialsettings` holds the two copies to the
same words. **The browser's bar** follows the choice too: both of the site's
theme-color metas (one for a light device, one for a dark) carry both
grounds, and Skribl's boot says the chosen one in each.

**The switch is kind.** A tap cross-fades the whole page into the chosen theme
in the site's own 0.28 seconds (a same-page view transition, the way a page
change already fades) while the pill slides there; under Reduce Motion the
page still fades and the pill is put there. A tap made while the page fades
(it lands on the page itself then) is kept, and its fade waits for the first
to end, so the page never jumps from half way. Never a flash: the next page
opens in the chosen theme from its first frame, because the boot stamps it
before anything paints. A browser without view transitions changes at once.

**Finding Settings.** (a) The gear says **Settings**: at the top right of your
own profile on a phone, in the Share button's dress (112 x 44 in this box's
font), and in your row of buttons on a desk, Edit profile, your face, Share,
then Settings (125 x 44). Nothing moves for it. (b) On a desk, **Settings in
the rail**, above your name at its foot, on every page (215 x 52), lit like
Home on Settings and the pages it leads to (Invites, deleting the account),
where You stays lit too, as the mock's picture has it. A phone's bar keeps its
four places, as it did for Activity. Not (c), a Settings row on your profile:
it would sit above your drawings.

**Signed out: nothing new.** No switch, no Settings: System follows the
device, and the Pad's and Flip's own switch (open to everyone through Make)
sets the one choice, so picking Dark there makes Blooby dark too.

**No other settings now.** The mock's list of what could come later (the
speed a drawing plays at, sound on, playing a post's drawing by itself, Tips
and Help cards, the bell, who can say something on your posts, taking your
drawings with you) waits for the owner to pick any.

**Pad and Flip:** nothing visible changes in either editor. Their switch
stays exactly as it is and now sets Blooby too; the one change is in
Skribl's head boot, which both share, and in `lib/theme.js`, which both load:
dark said out loud, which their stylesheets do not read.

`harness/verify_socialsettings.py` holds it through the demo's own server;
`verify_theme.py` holds the boot for any host. DECISIONS.md ("Settings: the
theme, one choice for Blooby, Pad and Flip") says what each check was shown
red by.

## 15. Built: mutes

From the mute mock and the owner's "Yes to all" (Nov 13): C, quiet
everywhere, and rule 3, mute and follow kept apart. Mute is a break from
somebody, not a wall: what comes to you goes quiet, and what you go to stays.
`social/mutes.py`:

    /social/@<handle>/mute      POST: mute them (JSON: {ok, muted, following})
    /social/@<handle>/unmute    POST: unmute them (JSON from the ⋯, the
                                toast's Undo or the line on their page; a
                                form from Settings, which comes back to it)

**Where.** "Mute @theo" in the ⋯ on somebody's page, first, the gentlest, and
on their posts and drawings after Copy link and Share…, before Report and
Block, so the two danger rows stay together; under it, what it does: "Their
posts, comments and likes stop reaching you. They aren't told." Its icon is
a closed eye drawn in our pen, never a speaker (a drawing's own sound switch
is the speaker). The row is the sheet's own (17px at 600, its words starting
where Report's and Block's do, its eye centred on the other icons), with a
second line as Make's doors have. Signed in alone; never on your own; muted,
it says "Unmute @theo" and "Everything comes back, just as it was."

**Nothing is asked first.** The tap mutes. The sheet goes down; on Home every
card of theirs folds away from where you are (it fades, then its room closes
and the next post rises into its place); on their page a line opens under
the buttons; a post's own page stays as it is, since you went there. Once the
sheet has gone and the site has said yes, a toast rises: "Theo is muted.
They aren't told." with Undo, for seven seconds, the Pad's own time for an
Undo; on a phone 12px above the bar, on a desk at the foot of the page in the
middle of the column, clear of the rail. Only Undo takes a tap: a tap on its
words reaches the page under it. Undo brings everything back the same way and
says "Unmuted. Theo's posts are back." A refusal puts everything back and the
toast says why. Under Reduce Motion nothing glides: a room is put there or
away only while what it holds can't be seen, and the fades remain.

**What goes quiet** (C), for you alone:
- Home, Following and Everyone: their posts, left out in the query, so every
  page stays whole (Home holds posts only since the map's step 3);
- Explore, and Skribl's other listings of everybody's: their drawings,
  through the feed filter the host installs (below);
- comments, on what you read and on your own: their comment or answer is one
  quiet line in its place, in Activity's own voice: "Someone you muted said
  something. Show" ("… answered." for an answer), the eye where their face
  was. The whole line is the button; Show opens it for that visit (the line
  fades, the room opens, the comment fades in). The comment is hidden for
  real while folded (no tap or screen reader reaches its Answer or ⋯), and
  the answers under it, by others, stay as they are;
- Activity: their comments, answers, likes and follows leave it and never
  light the bell's dot; a group they were in says the rest ("Juno and Mira
  liked your post"). Nothing is deleted: Activity is worked out each time, so
  unmute them and every row is back.

**What stays.** Their page, which says "You muted Theo · Unmute" under the
buttons to you alone (to them and to everybody else their page is exactly as
it was, in its source too); their posts and their drawings' pages, their
Gallery on their page, a drawing's link page and its payload. The
visibility policy is untouched: a mute never hides a page.

**Counts and "Liked by…" stay true,** for everybody and for you: a folded
comment is counted, their like is in the count and in "Liked by…", their
follow in "Followed by…" (since the map's step 5, in the counts and the
lists).

**Rule 3: mute and follow stay apart.** Muting never unfollows (so nothing
changes on their side, not even their own list of who follows them), and
unfollowing never unmutes. Following them, the toast says "Theo is muted.
You still follow them." Their posts stay out of Home, Following too, until
you unmute; to unfollow, tap Following, as always.

**Settings** lists Muted just above Blocked, in the Blocked panel's own rows,
newest first: their face, name, @handle and Unmute; "You see less of them.
They aren't told, and nothing changes for them."; with nobody, "Nobody. If you
mute someone, they're listed here, and you can unmute them." Nobody a block
either way or a takedown hides is listed: somebody you muted and then blocked
is under Blocked, and back under Muted, still muted, once unblocked.

**Who may mute:** somebody signed in; anybody who is there for them (not taken
down, no block either way), never themselves; the token and Origin first,
then the limit (60 an hour, mutes and unmutes alike). Unmuting lifts your own
row, whoever it named. A mute is private: nothing on their side changes, and
they aren't told. Later, not now: muting words and tags, a mute for a while,
muting from an Activity row.

**A mute reaches Skribl's listings** through the feed filter the host
installs, which Skribl now tells which listing it is (docs/INTEGRATION.md, "A
filter can ask which listing it is"): a filter that names `author` is told the
one author a listing is narrowed to, or `None` for many people's. The host
leaves out `social.muted_authors(viewer_id)` only when it is `None` (the demo's
`app.py` does), so a mute quiets Skribl's listings of everybody's (the first
visit's gallery, Skribl's own /gallery) and keeps their page's Gallery and More
from. The visibility policy never hears of mutes.

**Data.** One table on the site's chain (migration `4cdc4af46a77`, after
`1757a4385be8`), `social_mutes`: `muter_id`, `muted_id` (both to
`social_people`, ON DELETE CASCADE), `created_at`; unique on the pair, never
yourself (`ck_social_mutes_not_self`); indexed by whose newest first
(`muter_id, created_at`: Settings) and by whom (`muted_id`: deleting an
account). Unmuting deletes the row. Whom you muted is one read a request, by
your public id and the pair's index, shared by the site's pages and the
host's filter, so Home reads it once whatever it shows. **Deleting is real:**
an account goes with its mutes both ways, in code
(`accounts.delete_person`, through `mutes.drop_person_mutes`); the CASCADEs
are the net. Privacy and docs/LAWYER-NOTE.md say mutes are kept, who and
since when.

**Pad and Flip:** nothing changes in either editor. Mute goes by who made a
post, so a muted person's Flips leave Home as their drawings do, and the
in-post player that Pad drawings and Flips share is untouched. The one change
on Skribl's side is the feed filter being told a listing's `author`, which is
no editor's.

`harness/verify_socialmute.py` holds it through the demo's own server;
`verify_hostseams.py` and `verify_createpost.py` hold the feed filter's
`author`. DECISIONS.md ("Mute at /social: quiet everywhere") says what each
check was shown red by.

---

## 16. The map: a post is the one thing people share

The owner, Nov 13, after Explore's card turned out to be a different card
from Home's: "I'm starting to think we should do the social site like
skribls.net. It's a social site already that we were going to drop skribl
into as a feature, like GIF, add image, add video, poll... we can have the
gallery which is just the skribls (not post) and library drafts as part of
profile? We are kind of getting disorganized and random. We can clean this
up." Then, to the map below and its defaults: "Yes on everything." And
after it: "Also gallery of everyone is a thing, then can select followers,
everyone, and more filters to come down the road."

**Why.** The original intent (docs/SKRIBLS-NET.md) was Skribl as a feature
of a social site: a drawing rides in a post the way a video does, beside the
photos, video, emoji, GIF and polls skribls.net's composer already has.
Section 1's three layers still say so. What drifted was the site's side: it
came to treat a post and a drawing shown outside a post as two kinds of
thing. Home held both, Explore borrowed Skribl's Gallery (its own card, its
own initials for faces, no heart and no comments), a profile's Skribls was
the Gallery too, and likes and comments each had two routes, one for a post
and one for a drawing outside a post. Two cards on the same site was the
first thing the owner saw of it.

**The map.**

| Place | What it is |
|---|---|
| **A post** | The one thing people share: words, and one thing attached, a drawing or a Flip (words optional). Likes, comments, Activity, mutes and reports are about posts. |
| **Home** | Posts: Following, or Everyone. |
| **Explore: the Gallery of everyone** | Drawings and Flips as drawings, each opening its post: Following, or Everyone, with more filters to come. Home's Everyone already shows everyone's posts, so Explore shows the drawings. Since Nov 14 every drawing and Flip the site's people shared, in a post or not (below, "The Gallery is every skribl"). |
| **A profile** | Posts · Gallery · Likes · Drafts (and Bookmarks between Likes and Drafts since part two: section 17). **Gallery** is the same Gallery with one person in it: every drawing and Flip they have shared, as drawings, each opening its post. **Likes** and **Drafts** are yours alone, on your own profile; Drafts are the drafts Skribl already keeps on your account (SkriblDraft). |
| **Make** | One composer, the same from the bar and from Home: words, and Draw or Flip. Built Nov 14 (section 17, "The composer is built"), with Yours beside Draw and Flip. |
| **Activity, Settings** | As built. Settings from the ☰ on a phone (and the profile's button), the rail on a desk. |

**The owner's decisions (Nov 13, "Yes on everything").**

1. **Every share is a post** (words optional). Your Gallery collects every
   drawing you have shared, each opening its post. This replaces the Nov 11
   A, "Home holds every drawing, posts or not".
2. **Drawings already shared without a post stay in their author's Gallery**,
   so nothing is lost: the Gallery shows them, and Home shows posts from
   then on.
3. **Photos, GIFs, video and polls: not now.** The composer keeps room for
   them in the same place a drawing goes. skribls.net has them already. A poll
   would be the easy first one. Photos and video bring storage that grows
   with use (a bill: asked first, WORKING-AGREEMENTS "Spending") and a
   child-safety duty to scan and report; a GIF needs an outside service. Each
   comes with its own plan and the owner's yes.
4. **The look, from the quick-patterns mock**
   (https://claude.ai/artifact/S7171kFpfXxiLUzPLJJYwY, its defaults):
   - **One calm card for every post** (its B): at rest, who made it, the words,
     the drawing with its play button saying "drawn in 5 sec" (as Explore's
     does today), and one row. Press play and the drawing's line (scrubbing,
     speed, loop, the likes' dots) glides open under it and stays. A post's
     own page shows the line from the start. Faces are the site's: the
     empty circle before somebody draws one, never an initial. (CHANGED
     Nov 19, the owner's "all yes" to the walkthrough's mocks, choice 9,
     with today's circle beside it: a face not drawn yet shows its initial
     on a card, a post's own page and Activity, as a comment's has since
     Nov 17. A Gallery tile's small face is still plain. Section 21.)
   - **One row under every card** (its B): 💬 count, ♡ count, Share, ⋯, and
     Open › at the end (taken off Nov 19, the owner's "completely remove
     open": a tap on a card opens it; DECISIONS.md, "Draw back, mocked").
     The heart moves into the row from the drawing's line
     (the line keeps the likes' dots, and the hearts still rise from them);
     the ⋯ moves from the head into the row; the plays sit beside the time,
     and nothing is said at none.
   - **A profile's tabs** in the pen's underline, as the bar marks the page
     you are on (its B), now Posts · Gallery · Likes · Drafts. The Gallery and
     Drafts tabs are mocked before they are built.
   - **A ☰ on a phone** at the top left of Home and Explore, opening the
     site's own sheet: Settings, Community rules, Privacy, Your reports, Sign
     out. Help joins it when there is a Help page. The profile keeps its
     Settings button; a desk is unchanged.
   - **Make stays in the bar.** A floating button would sit over every card's
     Share.
   - **You stays your face with the word "You".**
   - **Counts on every profile** (its A): "3 followers · 2 following", "New
     here" while nobody follows them yet, a following count only when it is
     not zero. The lists of who follows whom stay yours alone, opened by the
     counts on your own page, where they take the place of "Followed by…".
     This replaces the earlier Nov 13 B, "no counts, ever".
5. **The Gallery of everyone** (the owner's addition, the same evening):
   Explore becomes it, with Following | Everyone, and more filters later.
   Mocked (https://claude.ai/artifact/LXxXHjTX9JwjK4kGYL8Vuy) and answered,
   the owner: "Your picks are great": the tiles are B, DRAWINGS FIRST, a grid
   of the drawings themselves, two across on a phone and three on a desk,
   each the drawing on its paper with a small "▶ 15 sec" (a Flip's pages),
   the maker's face and first name under it (their whole name since Nov 14,
   "Your picks"), and the hearts and comments
   only when there are some; THE BAR SAYS "GALLERY", Blooby's Explore icon
   kept; A TAP OPENS THE POST, where it plays with its line from the start;
   FOLLOWING | EVERYONE on top (Home's own pill), New, Hot and search under it
   as today. A profile's Gallery tab is this grid with one person in it.

**What stays.** The three layers (section 1). Section 8's item 9: our own
build, not a copy of skribls.net; it is skribls.net's shape that is taken.
Skribl's own pages, its /gallery, and every seam a host uses, so Skribl can
still stand alone and still drop into skribls.net. Nothing changes in the Pad
or Flip. On Skribl's side one new option on the in-post player, a seam: a
post's line can wait until it is played (the site turns it on; Skribl's own
pages and other hosts stay as they are).

**What goes, as it is built.** Drawings outside a post in Home;
the likes and comments of a drawing outside a post (`/b/<id>/like`,
`/b/<id>/comments`), the few there are kept readable, nothing deleted; Home's
drawing card (`data-kind="s"`). Each goes in the PR that replaces it, with the
suites that held it. The first and the last went with step 3 (DECISIONS,
"Home shows posts only"). The likes and comments STAY (the owner, Nov 14,
"Keep likes and comments", once the Gallery held every skribl): a drawing
shown outside a post keeps its own, by section 17's rule, one drawing, one
conversation.

**The order**, one PR at a time, each finished before the next starts:

1. This map (docs).
2. The one card and its row, on Home and a post's page.
3. Every share is a post; Explore becomes the Gallery of everyone,
   Following | Everyone (its tiles mocked first).
4. A profile's tabs: Posts · Gallery · Likes · Drafts (the Gallery and
   Drafts tabs mocked first, with step 3's tiles).
5. The ☰ on a phone, and the counts.
6. Likes and comments on posts only; what goes, taken out. (Changed, Nov
   14: they stay on a drawing shown outside a post, and one drawing has one
   conversation; section 17.)
7. Add to Home Screen (the owner, Nov 13, after the map): a way to put
   Blooby on a phone's Home Screen, so it opens full screen like an app.
   Mocked first, once steps 3 to 6 are in. Built Nov 15 (below, "Add to
   Home Screen is built"). (The owner also noted that in
   Bluesky a speech bubble with dots means direct messages: our 💬 is the
   plain bubble, as Bluesky's replies are, and stays so.)

**Step 2 is built** (#892; DECISIONS, "The one card: calm at rest, and one
row"): the row under every card, the line that waits (`line_waits`), the
heart in the row and the post page's one ⋯. The notes written for it
before it was built are in this file's history.

**Step 3's first part is built** (DECISIONS, "Explore becomes the Gallery
of everyone"): Explore lists the site's own posts as their drawings
(`social/gallery.py`: the page at `/social/explore`, and a page of its tiles
at `/social/explore/more`, JSON, for Load more and a new pick), the tiles the
mock's B, Following | Everyone on top,
New, Hot and search under it, and the bar says Gallery. Its Hot is Skribl's
new seam, `recent_plays()` (docs/INTEGRATION.md, "What is played most, among
your own posts").

**Step 3 is built**, its second part too (DECISIONS, "Home shows posts
only"): Home's feed, Following and Everyone, signed in and out, holds posts
alone (`posts.feed_page`; one person's, More from, kept their drawings until
More from went, Nov 20). A
drawing shown in the gallery outside a post, the Pad's own or anything
shared before posts, is on no Home and was not in the Gallery of everyone
(it is since Nov 14: "The Gallery is every skribl", below); it keeps its own
page (`/social/b/<id>`), its maker's page (their Skribls then, their Gallery
since step 4) and More from, so nothing is lost. The first
visit is as it was: Skribl's own Gallery section, every public skribl (until
the small yeses after step 4, below). Next is step 4.

**Step 5 is built** (DECISIONS, "The ☰ on a phone, and the counts"),
before step 4 (a profile's tabs), built since. The ☰, drawn in our pen, sits at the
top left of a phone's Home and Gallery and opens the site's own sheet, the
⋯'s (`_menu.html`): Settings, Community rules, Privacy, Your reports (an
admin's alone: the page is nobody else's) and Sign out; signed out, the
same ☰ holds Sign in, Community rules and Privacy. A desk is unchanged.
Every profile says its counts under the @handle (`follows.counts`, counted
by whoever looks, as a like's count is): "3 followers · 2 following", "New
here" while nobody follows them yet, a following count only when it isn't
zero. On your own page the counts open your lists and took the place of
"Followed by…"; on anybody else's they are words, and the lists stay yours
alone. Where section 13 says nobody has a count on show, this is the
decision.

**Step 4 is built** (DECISIONS, "A profile's tabs"): where a profile's
Skribls heading and Skribl's Gallery section were, Posts · Gallery · Likes ·
Drafts on your own page and Posts · Gallery on anybody else's, Posts first,
the chosen tab marked with the bar's own pen line; each tab a link with its
own address (`/social/@<handle>`, then `/gallery`, `/likes`, `/drafts`), the
back button and a shared link landing on it, the line drawing itself under
each (since Nov 14; it glided at first) and the panel fading between them
(`profiles.py`, `_profile.html`, `tabs.js`). Posts and
Likes are Home's one card; the Gallery is the Gallery of everyone's tile
with one person in it, a drawing shown outside a post opening its own page,
so nothing is lost; Likes and Drafts are yours alone, nothing of either on
anybody else's page or in its source. Drafts are the ones Skribl keeps on
your account, listed through its new seam `list_drafts()` and opened in the
Pad or Flip with `?draft=<id>` (docs/INTEGRATION.md, "A person's drafts on
your own page"). SINCE NOV 19 A TAP ON A DRAFT'S TILE OPENS IT INSIDE A POST
(the owner's "All yes" to the walk of Save and Drafts: that link left the
site for the editor by itself, with no way back): the composer's sheet with
the editor over it, as "Use one you made" opens one, the sheet unseen until
Add; the link is still the tile's own, for a new tab (`compose.js`,
`SocialComposer.draft`; `verify_socialprofile` 20). Next was step 6, which
the owner changed (section 17).

    /social/@<handle>            Posts, which opens first
    /social/@<handle>/gallery    the Gallery
    /social/@<handle>/likes      Likes, yours alone (anybody else: the page)
    /social/@<handle>/drafts     Drafts, yours alone (anybody else: the page)
    /social/@<handle>/more       a tab's first page or its next, ?tab= and
                                 ?before= (JSON {html, next, tab})

**Six small yeses after step 4** (the owner, Nov 14; DECISIONS, "Six small
yeses"). A TILE WEARS ITS DRAWING'S OWN GROUND: the box around a drawing whose
shape is not the tile's is the colour the drawing is painted on, the Pad's
dark for a drawing made on it, never cream bars; the paper where it is not
known; Skribl's `describe_posts` says it (`ground`, a hex colour or nothing:
docs/INTEGRATION.md), in the Gallery and a profile's Gallery tab (and on a
draw-back's tile, since More from went, Nov 20).
A TILE SAYS THE NAME AS WRITTEN ("Mr. Blood"), cut with … only when it does
not fit. THE FIRST VISIT (Home signed out) keeps its welcome, and under
"Fresh from everyone" the Gallery of everyone's six newest (posts only then;
every skribl since, below), then
"See the whole Gallery ›", where Skribl's own Gallery section was; with
nothing shared, the Gallery's own words. "LIKED BY" LEAVES THE MAKER OUT
(above, section 12). NO "MAKE YOUR OWN" ON A POST'S PAGE: Make stays in the
bar and the rail. DELETING A POST FROM YOUR OWN PAGE keeps you there, the
post folding away where it was; from a post's own page it still lands on
Home with its note. And the answer to step 4's question: a mute does not
take that person's posts out of your Likes, which are your own record of
what you did.

**The Gallery is every skribl, and the eye** (the owner, Nov 14; DECISIONS,
"The Gallery of every skribl"). To the Gallery as built, posts only: "I
thought gallery was only skribls (pad or flip)?", then "Yes, your picks".
This changes the map's word for the Gallery, and for the Gallery only:
Home stays posts. THE GALLERY OF EVERYONE (Following and Everyone, New and
Hot, a search), THE FIRST VISIT'S SIX and A PROFILE'S GALLERY hold every
Pad drawing and Flip the site's people shared, in a post or not: a post's
drawing opens its post, one shown outside a post its own page
(`/social/b/<id>`), with its length, its maker's face and whole name, and its
hearts and comments when there are some. Never a face, a comment's drawing,
one kept link-only, or one by somebody not on the site (Skribl's own /gallery
keeps those). New and Hot hold both kinds in one order, Load more walks both
by one cursor, and the search reads a post's words, a drawing's title, and
the maker's name and @handle: two reads a page long, the site's posts and
the rest through Skribl's new seam `shared_skribls()` (docs/INTEGRATION.md,
"Your people's drawings beside your own posts"), merged in one order.
THE EYE, on your own Gallery tab alone ("Yes, the eye in view"; "The stage
is too much to show, but there should be a gallery toggle in profile
library"): each of your tiles wears a small eye at its top right; one tap
hides the drawing from the Gallery (the eye crossed, "Hidden", the drawing
faded, the site's toast "Hidden from the Gallery" with Undo), tapped again it
is back. A post's drawing by the site's own flag on the post
(`social_posts.gallery_hidden_at`): the post stays on Home, in your Posts and
everywhere a post is. One shown outside a post by its visibility in Skribl,
public ("In the gallery") or link-only, as the Library's own switch changes
it; your link-only ones are on your own Gallery tab, hidden, and their page is
yours alone. Nobody else sees the eye, in the page or its source. AND A POST
DELETED FROM YOUR OWN PAGE says so in the same toast, near the finger ("Yes",
the answer to the six small yeses' question): "Your post is gone, its drawing
with it.", no Undo, a delete is final. The toast never covers a button
someone is pressing fast: where an eye, or the next card's ⋯, would be under
it, it rises just above them.

    /social/p/<id>/gallery          your post's drawing in the Gallery, or not
                                    ({"gallery": true|false}, JSON)
    /social/b/<skribl_id>/gallery   your drawing shown outside a post, the same

**A drawing on a photo keeps its photo at its sides** (the owner, Nov 14,
"Yes to both, build them"; DECISIONS, "A drawing on a photo keeps its photo
at its sides"). Asked on their phone, on a profile's Gallery tab: "will the
player not show the strips on the side?" A TILE OF A DRAWING MADE ON A
PICTURE, a photo or the picture the Pad began on, shows that picture at its
sides: a second copy of the drawing's plate behind it (`_gallery.html`
`plate_fill`), scaled to cover the box a quarter over, blurred 16px, a little
more saturated and at 0.9, so a photo is never framed in cream or dark bars.
A drawing on a plain ground keeps its strips in its own ground, as before: on
a line drawing the blur is a coloured haze. The ▶ and, on your own Gallery
tab, the eye stay on top of every tile (the copy comes first in the box and
nothing has a z-index; the first mock lifted the drawing over the ▶ and the
owner saw it). Every tile that frames a plate: the Gallery, a profile's
Gallery tab and the first visit's six (and More from, until Nov 20). Hidden with the eye, the
picture at its sides fades with the drawing. Skribl says which drawings are
on a picture (`describe_posts` `on_photo`), from a column written at post
time beside the ground's (docs/INTEGRATION.md, "The ground a drawing is
painted on"); a drawing from before the columns is read from the drawing
until `python -m skribl.backfill_ground --write` is run, which is optional:
nothing breaks without it.

**A list of choices is one card, and the ☰'s equal lines** (the owner, Nov
14, "B, equal lines"; DECISIONS, "One card for a list of choices, and the
menu's equal lines"). On the ☰'s sheet, each row its own rounded card and an
outlined Cancel under them: "Do we need everything to be in a pill? It
starts looking weird when everything is in one everywhere... look for all of
them across entire app. Not pill sliders but like the screenshot." EVERY
MENU SHEET OF THE SITE, the ☰'s, a post's ⋯ (yours and somebody else's), a
comment's ⋯ and a person's ⋯, holds its rows on ONE CARD, as the Pad's own
menu list draws it: the rows on it with nothing of their own behind them, and
between two Apple's thin line (the owner's "Apple's thin line", to the mock
beside no lines and three lines with depth): one screen pixel, from where the
row's words start to 16px before the card's edge, in `--row-line`
(`social.css`, "THE ⋯ SHEET" and "THE LINE BETWEEN TWO ROWS"). The risky rows (Report, Block, Delete, Remove from my post)
are a card of their own, 12px under the other; a comment's ⋯ holds only
those. THERE IS NO CANCEL under a menu sheet: its grip, a tap outside it, a
swipe down and Esc close it, as they close the Pad's menu. Report's reasons
are one card the same way. Kept as they were: Report's Cancel | Send report,
Mute's and Block's pairs, Make's two doors, Your face's three ways and the
Settings page's cards. The ☰ itself is three lines of one length. Skribl's
own sheets did the same on the Pad and Flip (Export's formats, Your drafts):
one look across the site and the editors.

**The four.** Simple: one thing to share, one card for it, one Gallery
(everyone's, the people you follow, or one person's), one place for your
things. Kind: nothing anybody made is lost, Likes and Drafts stay yours
alone, nothing covers a button. Playful: the drawing still draws itself in
every card, and your Gallery is your drawings as drawings. Powerful: Skribl
drops into skribls.net exactly as it drops into our site.

## 17. The map, part two: what any social site has

The owner, Nov 14, after the map's steps 1 to 5 were built: "Keep likes and
comments. Not sure how likes and comments work on pads/flips and posts?
Let's think about how that might work. Sign up is needed, reposts are
needed, push notifications (not sure what they are), Bookmarks I didn't mean
to say no to that. We need direct messages. We need all the things that any
social site has." Then "Yes" to the rule and the order below. Each piece is
mocked first, light and dark, phone and desk, and asked for before it is
built.

**One drawing, one conversation.** A post's hearts and comments are the
post's; its drawing has no count of its own. A drawing shown outside a post
(the Pad's own share, `/social/b/<id>`) keeps its own hearts and comments.
When an older drawing is posted (the composer's "Yours"), its hearts and
comments move onto the new post and its own page sends people to the post:
nothing is lost, and there are never two conversations about one drawing. A
drawing is in one post; sharing it again is a repost. A repost shows the
original, and its hearts and comments are the original's (as on Bluesky); a
quote post is a repost with your own words, or your own drawing. A Gallery
tile shows that one conversation's counts.

**Push notifications**, said plainly for the owner: the alerts a phone shows
on its lock screen ("Rook liked your drawing") when the site is not open. An
iPhone lets a website send them only once it is on the Home Screen, so they
follow step 7.

**The order**, one PR at a time, as part one:

1. The composer (the owner's yes, the morning of Nov 14): one Make sheet
   everywhere, words and a drawing; "Yours" posts an older drawing, its
   conversation moving with it. Quote posts reuse it. Built (below).
2. Bookmarks: save a post; yours alone. Built (below).
3. Reposts, then quote posts. Built (below).
4. Mentions: an @handle in a post or a comment links to that person and
   tells them. Built (below).
5. Finding people: search by name or @handle. Built (below).
6. Open sign-up, with what it needs to stay kind (limits for new accounts,
   the admins' tools); the owner's rules asked when it is mocked.
7. Add to Home Screen (part one's step 7), then push notifications. Both
   built: Add to Home Screen below, push notifications in section 19.
8. Direct messages: one to one, a drawing as easily as words, who may
   message you, and a requests inbox.
9. The smaller things most sites have: pin a post to your profile, edit a
   post's words (shown "edited"; the owner's yes), tags, download your data,
   and words that describe a drawing to a screen reader.

**The composer is built** (part two's item 1; DECISIONS, "The composer: one
Make, and an older drawing's conversation comes with it"). ONE MAKE,
EVERYWHERE: for somebody signed in, Make (the bar on a phone, the rail on a
desk) opens the composer on every page with the bar (`_compose.html`,
`compose.js`, `compose.py`). HOME HAS NO BOX AT THE TOP (the owner, Nov 14:
"Why not make as way to post? Do we need post at top?", then "All yes" to
the mock without it): Make is the way to post, and Home opens on its pill
and its posts, 164px higher. On
a phone it rises almost to the top and rides above the keyboard (social.js's
SocialKeyboard, which a comment's sheet shares: it reads the keyboard again
until it rests, since a phone can report a size the keyboard only passes
through and then say nothing; the owner's iPhone, Nov 14); on a desk it is
a 600px card in the middle. ON A PHONE IT OPENS CALM (the owner, Nov 20, with
two pictures: "Ours opens like 1st shot and should start like 2nd
screenshot"): the sheet itself takes focus, at its full height, and the
keyboard comes when the words are tapped; with a keyboard of its own (a
desk) the words take focus as it opens. Cancel at the top left, Post at the top
right, dim until there are words or a drawing; your face beside "Say something…";
the drawing under the words, playing, with Edit drawing and Remove; Draw,
Flip and Yours along the bottom, and the characters left (500). Draw and
Flip open Skribl's editor over it in compose mode, as Home's did. YOURS is
"Use one you made", the one pill Drafts | Drawings: a draft opens in the
editor that made it, over the sheet, with the draft on its canvas
(Skribl's `lib/composehost.js` `openDraft`, docs/INTEGRATION.md "A saved
draft, from your own list"), and Add to post attaches it; a drawing you
shared outside a post (link-only too) is attached as it is, and posted, it
is the post's drawing: ONE DRAWING, ONE CONVERSATION, its hearts and
comments moving onto the post in the same transaction, its own page
(`/social/b/<id>`) sending people to the post, Activity naming the post at
the times it always had (nothing new, nobody told twice). A drawing in a
post is not offered again. Signed out, Make keeps its two doors into
Skribl's own Pad and Flip, whose own share stays Skribl's.

**The page is Pad's** (the owner, Nov 14: "background color on /social? Here's
flip and pad", then "Yes, A", choosing the site to follow the editors rather than
the editors the site): the site's ground is the editors' column surface
(styles.css `--surface-raised`, #f6f8fa light and #0f1218 dark) with its
purple glow at the top, one screen tall, and the browser's bar wears it
(social.css `--page`, base.html's theme-color; verify_socialsettings holds
both to styles.css).

    /social/make/yours     "Use one you made", a page of its tiles: ?tab=drafts,
                           or ?tab=drawings (and ?before=, Load more), as
                           {html, next, tab} (JSON); yours alone
    /social/posts          also {"words", "skribl": <your drawing's id>}: an
                           older drawing as a post, its conversation with it

**Bookmarks are built** (part two's item 2; DECISIONS, "Bookmarks"; the
owner's "All yes", Nov 14, to the mock's A, the fifth tab, and nobody told).
IN THE ⋯: "Bookmark" first in the ⋯ sheet's first card, on every post and on
a drawing shown outside a post (its own page's ⋯ is the same sheet), your own
too; its ribbon drawn in our pen (`_icons.html` `ribbon`) in the row's ink.
Once kept the row reads "Remove bookmark" and the ribbon is filled in the
small violet ink (--accent-ink, 8.26:1 on the card light, 8.39:1 dark; the
action's purple, --fill, was 2.99:1 on the dark card). None on what is taken
down or a drawing kept link-only, as the heart. The row under a post is
unchanged. A tap keeps it (or takes it away), the sheet goes down, and the
site's toast says "Bookmarked. It’s on your page, under Bookmarks." (or
"Removed from your bookmarks.") beside the ribbon, with Undo, clear of every
⋯ on the page (`SocialToast` `clear`); Undo puts it back and says so, with no
Undo of its own. Signed out, Bookmark raises the heart's small sheet,
"Bookmark this post?" ("Sign in, and it’s kept for you on your page, where
only you can see it.", Not now | Sign in, back to the page), and nothing is
kept. YOURS ALONE: a fifth tab on your own page, Posts · Gallery · Likes ·
Bookmarks · Drafts, never on anybody else's page or in its source (its
address sends anybody else to your page, as Likes'), listing what you kept as
Home's cards, newest kept first, Load more (`bookmarks.marked_page`). Hidden
from it, never deleted: a block either way, anybody taken down, a post taken
down (your own shows with its note, as on Home), a drawing its own page no
longer shows you (made link-only, deleted in Skribl). Somebody you muted
stays: you chose it. On a phone your own five tabs are SIZED TO THEIR WORDS
("Bookmarks" is wider than a fifth of a phone: about 24px between words,
16px at the edges; short of room the edges give first, then the tabs, never
past the screen); a desk keeps
equal columns; the pen's line is the chosen tab's own (drawn inside it), so
it is under it before any script runs, and tabs.js moves it on a tap. NOBODY
IS TOLD: no Activity row, no dot, no count anywhere; a page says only
whether one is the viewer's own (`data-marked`, theirs alone). One drawing,
one conversation: an older drawing posted through Yours takes its bookmarks
onto the post with its hearts and comments. Deleting a post, a drawing (on
the site) or an account takes its bookmarks, in code. The table is
`social_bookmarks` (a migration of the table and its indexes alone). Pad and
Flip: nothing changes in either.

    /social/p/<id>/bookmark         POST {bookmarked}: your bookmark on a post,
                                    kept or taken away ({ok, bookmarked})
    /social/b/<skribl_id>/bookmark  the same, on a drawing shown outside a post
    /social/@<handle>/bookmarks     Bookmarks, yours alone (anybody else: the page)

**Reposts and quote posts are built** (part two's item 3; DECISIONS,
"Reposts and quote posts"; the owner's "All yes", Nov 14, to the mock's five
asks and its defaults). THE ROW UNDER A POST is comment · repost · heart · ⋯
· Open › (a post's page and a drawing's without Open ›): the repost takes
Share's place, and Share… and Copy link are the ⋯'s. The repost is the two
arrows (`_icons.html` `repost`) and how many reposts and quotes, none at
zero, counted by the viewer as hearts are; once the repost is yours both are
in the small violet ink (--accent-ink, 8.26:1 on the card light, 8.39:1
dark). Three counts in the hundreds still fit a phone: the counted three
give a little of the room past their counts. A TAP raises its own small
sheet, the ⋯'s shape (`#repostSheet`): "Repost" ("Show it to the people who
follow you"), or once yours "Undo repost" ("Take it off your page and your
followers’ Home"), and "Quote" ("Repost it with your own words, or a
drawing", the bar's Make pencil); a drawing shown outside a post shows Quote
alone (only its maker posts it). Repost asks nothing more: the row lights
and its count moves at once, the count fading and the button growing round
the arrows (no toast; Undo is the sheet's own row). Signed out, "Repost
this post?", the heart's small sheet. A REPOST IS NO POST OF ITS OWN (one
drawing, one conversation): it is the original's own card, its hearts and
comments its own, with "Mira Lopez reposted" at its top ("You reposted" for
yours; the @handle's ink, 7.56:1 light, 8.59:1 dark), on Home's Following
for the people who follow the reposter and on the reposter's Posts tab,
merged newest first under the one cursor; Everyone shows posts only; the
same post twice in one page shows once, the newest; never by somebody you
muted or of their post on Home, nothing a block hides, nothing taken down.
A QUOTE is a post with the original small inside it (`_gallery.html`
`quote_card`): its author's name and @handle and when, its words two lines
at most, its drawing as the Gallery's still picture with "drawn in", one
link to the original. AND THE DRAWING IT LEADS TO, HOWEVER DEEP (the
owner's "all yes" to "Just a Border", Nov 16): an original with no
drawing of its own that is itself a quote shows the drawing its own
original has, through as many quotes as it takes, as a quote of a drawing
shows it, until a post the person looking may not see; Make's small card
the same. Inside a post's card the small card is a well, a clear lilac
and no line (D2; a chosen lilac since No dinge, Nov 16). Its own words, its own drawing, or both: a quote of
words alone has no drawing of its own. Quote opens the composer
(`window.SocialComposer.quote`) with the original small under the words,
"Add your words, or draw something…"; Post wakes once there are words or a
drawing; Make opens the composer without the quote. A QUOTE OUTLIVES WHAT IT
QUOTES: once the original is deleted, or hidden from the person looking (a
block either way, taken down), its small card says "This post is gone."
WHO IS TOLD: the original's author, in Activity ("Mira reposted your post",
to the post, several since you last looked one row; "Rook quoted your post",
to the quote, its words under it), each face wearing the arrows; Undo repost
takes its row away; nobody muted; neither lights the bell's dot. Deleting a
post takes its reposts and its quotes let go of it; an account the same, in
code. The data: `social_reposts` (who, which post, whose, when) and four
columns on `social_posts` (`is_quote`, `quoted_post_id`,
`quoted_drawing_id`, `quoted_owner_id`), `skribl_id` no longer required
(a migration of the table, the columns and their indexes alone). Pad and
Flip: nothing changes in either.

    /social/p/<id>/repost           POST {reposted}: your repost of a post, made
                                    or undone ({ok, reposted, n})
    /social/p/<id>/quoted           the post, small, as the composer shows it
                                    under the words of a quote ({html})
    /social/b/<skribl_id>/quoted    the same, for a drawing shown outside a post
    /social/posts                   also {"words", "quote": <a post's address>}
                                    or {"quote_drawing": <a drawing's id>}, with
                                    or without a drawing of its own

**Mentions are built** (part two's item 4; DECISIONS, "Mentions"; the
owner's "All yes", Nov 15, to the mock's three asks and its defaults). HOW A
MENTION LOOKS (A): an @handle that is somebody, in a post's words, a
comment's or an answer's, and a quote's own words, is a link to their page in
the small violet ink (--accent-ink, 600, never underlined: 8.26:1 on the card
light, 8.39:1 dark; 7.75:1 and 9.89:1 on a comment's ground), the words' own
size and line, so nothing else in the words moves. A handle that is nobody
stays plain words, and so does every one past the first ten people named in
one post or comment. The words are escaped first, as any words are, and only
the handles the post or the comment keeps as its mentions become links
(`mentions.said`); where the words are already one link (Activity's peek, a
quote's small card) they stay plain. A card's words are
no link of their own any more (a link cannot hold the links to the people
they name): a tap on them opens the post as the card's ground does
(posts.js), a tap on a mention opens the person and never the post, and a
drag that selects them opens nothing. THE LIST UNDER AN @: typing an @ in the
composer or in a comment's box (answers too) shows, right under the line
being typed and over what is there (nothing moves, the sheet is not pushed),
the people you follow first (their @handle, or any word of their name,
starting with what follows the @), then anybody whose @handle or name starts
with it (any word of it, since finding people, below), by name, four at most: each row 52px, their face, their name and
their @handle, on the mock's card (`mentions.js`, `_mentions.html`). Where
there is no room under the line (a phone's comment sheet, sitting on the
keyboard) it opens over the line, so on a phone it stays above the keyboard.
A tap, or Enter or Tab on the highlighted row (the arrow keys move it, Esc
closes the list and nothing else), puts "@handle " in where the typing was,
and the field keeps its focus. Nobody a block hides either way, nobody taken
down, never yourself. It fades in, and under Reduce Motion is simply there; a
screen reader hears a listbox of options (the field's aria-expanded and
aria-activedescendant). WHO IS TOLD: the person mentioned, in Activity,
"Rook mentioned you", a row each, their words under it in quotes, the post's
small picture (a comment's own drawing, else the post's), their face wearing
an @ on the follow badge's purple disc; it opens the post, or the comment on
its page, glowing; and it LIGHTS THE BELL'S DOT, as a comment does. Never
from somebody you muted (quiet, as their comments are), never through a block
either way (the link still shows; their page is nobody's to the one blocked,
as it was), never yourself, never about anything taken down or that you
cannot see. A comment on your post, or answering you, that also mentions you
is one row, the comment's; so is a quote of your post that mentions you, the
quote's. KEPT AS TYPED: `social_mentions` (who was mentioned, the handle as
typed, who wrote it, in a post or in a comment, exactly one, a CHECK; whose
the post is or what the comment is on; when), written in the same transaction
as the post or the comment and never changed after (posts can't be edited
yet, so a mention is fixed once posted); the link goes to the person by
their id, so a handle that changes never breaks an old one. Read once a page
for all its cards, once for all its comments. Posts written before mentions
keep their words plain: nothing works mentions out of old words (a migration
of the table, its indexes and one index on the people's names in small
letters, alone). Deleting a post, a comment (every way one goes) or an
account takes its mentions, in code. Pad and Flip: nothing changes in either
(mentions are the site's words; Skribl's own titles take none).

    /social/people/suggest?q=<what follows the @>
                                    the list under an @: {people: [{handle,
                                    name, face}]}, four at most; signed in
                                    (401 otherwise), 600 an hour

**Add to Home Screen is built** (part one's step 7, part two's item 7;
DECISIONS, "Blooby on the Home Screen"; the owner, Nov 15: "Let's do the home
icon so I can get full screen on my iPhone", then "All yes" to the mock).
THE SITE'S OWN APP: every page of the site's links the site's own manifest
(`/social/manifest.webmanifest`, a route so its URLs follow the mount
points): Blooby, opening on Home, standalone (full screen, no browser bar),
the site's dark ground; its scope the folder the site and Skribl's pages
share, so the Pad, Flip and the Library a post or Make opens stay inside
the app. THE ICON IS BLOOBY.APP'S (the owner's pick, Nov 13: waving Blooby
on the lilac, no star, 82% tall; filed in `docs/brand/`), drawn from his
strokes by `harness/tools/blooby.py site-icon` into the site's own files
(`social/static/blooby-icon-*.png`): the touch icon, the page icon, the
manifest's, and Blooby in small on the sign-in pages, the kind pages and
Activity's empty state. Skribl's pages keep Skribl's manifest and icons
(Skribl, Blooby on the white star, opening the Pad). HOW YOU ADD IT: on an
iPhone or an iPad in Safari, the ☰ on Home and the Gallery has Add to Home
Screen right under Settings (Sign in, signed out); it lets the ☰ go down and
the steps rise (the site's own sheet: the icon and its name as the Home
Screen shows them, iOS 26's three steps, "It may ask you to sign in once
there, with your passkey", Got it). On Android the row shows once Chrome
offers its own install, and asks Chrome. A desk sees neither. FROM THE HOME
SCREEN the same row says Reload, as there is no browser bar to reload with.
The Pad's and Flip's own steps say iOS 26's too. THE SPLASH (the owner, Nov 15,
with Bluesky's: "make a splash screen load first and show blooby", on the dark
ground "with no stars", then "All yes, B with the stage spotlight"): the app,
once a launch, opens on the night ground (the site's dark ground deepening to
a deep purple), where a still spotlight of the icon's lilac comes up on
Blooby, who jumps with his hands thrown up (the Posted! card's seven poses,
drawn by the real Pad without the badge, the last just him with his arms up)
and lands back in its pool, while "blooby." in the site's purple writes itself
under the stage (its middle at 70% of the screen) the first time and its blush period falls, squashes and pops back
as skribl's i-dot does; later launches have the word already there; then it
fades into the page (`splash-boot.js` decides before the first paint and asks
for the show's two pictures, `splash.js` plays it, the word with Skribl's
player; a tap skips it, Reduce Motion keeps it still, a picture that does not
come never holds the page, and the page's own drawings wait for it). The
light is what lets his dark outline show (5:1 and more at every pose; 1.1:1 on
the night alone). The Pad's and Flip's hello at blooby.app falls the same way
now. THE APP'S TOP EDGE (the owner, Nov 15: "the top bar is fuzzy on top"):
iOS 26 lays a glass blur over the top of a Home Screen web app; in the app
(`is-app` on <html>, from `splash-boot.js`) every page has a 6px strip of its
own ground fixed at the top, which WebKit reads as an opaque edge and so draws
no blur there. It cannot be seen: the page scrolls under it as under the
phone's bar. The Pad and Flip, which open inside the app, have their own
since Nov 15 (Skribl's, styles.css: `data-skribl-app`, marked before the
first paint by `_skribl_app_boot.html`); nothing of the site's reaches them.

    /social/manifest.webmanifest    the site's web app manifest (Blooby,
                                    opening on Home)

**Finding people is built** (part two's item 5; DECISIONS, "Finding people";
the owner's "All yes", Nov 15, to the mock's A and every default). THE
GALLERY'S SEARCH FINDS PEOPLE TOO: its box says "Search people and drawings"
(to a screen reader too), and with a search a People section comes first, up
to three people, then "See all" when there are more, then Drawings, the tiles
as before; no search, the Gallery as it was. It sits in the part of the page
that fades, so a search's people come and go with its tiles, changed only
while they can't be seen; Following | Everyone and New | Hot change the
drawings alone. A PERSON IN THE RESULTS is the mock's row, 64px: their face
(44px), their name (17px 600, the first ink) and their @handle (15px, the
second), cut with … only when they don't fit, and Follow exactly as on their
page (Follow, Following, asked once to unfollow; signed out, the sheet that
asks you to sign in, coming back to the search as it is); a tap anywhere on
the row but Follow opens their page; your own row has no Follow, as your own
page has none. WHO IS FOUND: anybody whose name, by any word of it, or whose
@handle starts with what was typed ("pa" finds Theo Park; "ar" finds nobody
by the middle of his name), case, accents and a leading @ put aside, and
anything else that is not a letter or a digit read as a space; the people you
follow first, then everybody else, each by the word that found them; nobody a
block hides either way, nobody taken down, signed out too; somebody you muted
is found (their page stays open to you). SEE ALL is the same page asked for
the people alone (`?who=people`): "People", the box, twenty a page and Load
more, no pills, the address shareable and the back button going back to the
Gallery's search as it was. THE WAYS OF FINDING SOMEBODY are rows of their
own, `social_people_words` (their name from each of its words on, and their
@handle, folded), written in code with the name, on joining and in Edit
profile, so a name changed is found by its new words at once and never by
its old; every read is on an index (your follows and their ways, then
everybody's ways), the same few a page however many are found. The people
already on the site are given theirs in code, never by the migration (a
table and its indexes alone): `flask social words --write`, which
gunicorn.conf.py runs once each start right after the site's chain, and
anybody may run by hand (without --write it says how many have none). The
list under an @ (mentions) finds the same people the same way. Pad and Flip:
nothing changes in either (Skribl's own /gallery keeps its own search).

    /social/explore?q=<words>       the Gallery: People first (three), then
                                    Drawings
    /social/explore?q=<words>&who=people
                                    See all: the people alone, twenty a page
    /social/explore/more?q=<words>&who=people[&before=<cursor>]
                                    a page of them ({html, next}); and a new
                                    pick's /explore/more brings {people}, its
                                    People section

## 18. The comment thread (the owner's yes, Nov 17; built in three steps)

The owner, Nov 17, with a picture of another site's comments: "take a look
at this comment format. does it look like it would work for what we are
doing? ours looks a little sloppy?", then, with a second picture of bordered
comments, "also consider the bordered comment to show separation?". Three
mocks followed, each answered, and a yes to the last. The owner's weekly
limit ran out at the yes, so this section began as the plan; its three
steps are built now ("Built: step 1", "step 2" and "step 3", at the end),
and section 10 says what step 1 changed there. Each mock shoots the site's own post page on a phone and a
desk, light and dark, with now beside the options:

- [The Comment Thread](https://claude.ai/artifact/QmpBByK9hUwrZLxn317sCa):
  now, A (open) and B (bubbles). The owner: "I like B, bubbles, but I think
  it should have the same choices as a post - reply, likes, repost,
  bookmark, copy link, share, delete. don't you think? "reply" works better
  than answer to me also. no need to show the words on a phone. also how
  would you handle a reply to a reply to a reply and so on? mock that first"
- [Replies to Replies](https://claude.ai/artifact/AgEnrGVMviaEFRms6ZWPmt):
  one level (with the @name), two levels and every level, and the post's
  choices on every comment. The owner pointed to Bluesky instead: "(which
  goes more than 2 deep (which is too far for us), but see on the first one
  where it says Read 2 more replies - then the second shot opens that screen
  to the reply and shows the replies to that reply."
- [Read More Replies](https://claude.ai/artifact/XbQmHKjA2swkoMkCwfdUjo),
  the yes: two levels, then "Read N more replies", which opens the reply's
  own page, built in three steps. The owner: "I like it. not sure how you'll
  handle drawings in there, but.. what I would like to do is say yes to this
  most recent mock".
- [A Comment Shared](https://claude.ai/artifact/4XKrYxE3894YErstqr88NW),
  step 3's own (Nov 17): a comment away from its thread, reposted on Home,
  quoted, kept in Bookmarks. A (the way to it above, as on its own page) or
  B (alone, with "On Ben's post" under its name), and quoting a comment or
  Repost only. The owner: "All yes" (A, and quoting).

`harness/tools/mock_comments.py` shot the last one and shoots it again: the
mock's look laid over today's page, with nothing in the app changed. Start
the next mock from it.

**What the yes says.**

- **Bubbles (B).** A comment's name, time and words sit in a bubble: the
  site's card (`--card`) with its lilac edge (`--card-edge`, one screen
  pixel) and its lift (`--card-drop`), as a post's card wears. It is 18px
  round and as wide as its words. The lift is not decoration: in light, a
  white card on the near-white page is 1.06:1, and Just a Border asks for
  1.08:1 or a lift. The words read 18.0:1 light, 14.1:1 dark. There are no
  divider lines between comments. The glow on a comment you came to stays
  visible, because the bubble is not lilac.
- **A face not drawn yet shows its initial** in the site's disc (`--tint`,
  the letter in `--accent-ink`: 6.5:1 light, 6.9:1 dark). The count beside
  "Comments" sits in a small pill of the same lilac.
- **The thread's line** is a soft lilac, 2px of `--card-edge` (1.47:1
  light, 1.45:1 dark: there to be followed, not read). A reply hangs from it
  on a curve out of the face it answers. Each line stops where its branch
  stops, so none hangs past the last reply.
- **The post's choices on every comment.** Under each bubble is the post's
  own row with its icons: Reply, Repost, Like with its count, and ⋯ (7.1:1
  light, 10.1:1 dark). The ⋯ opens the post's sheet, titled "This comment":
  Bookmark, Copy link, Share…, then Report this comment on somebody else's
  or Delete comment on your own. On your own post or drawing, Remove from
  my post stays, as today. There is no thumbs-down: a dislike count on
  somebody's comment isn't kind.
- **"Reply", never "Answer"**, wherever the site says it:
  - the button;
  - the box ("Reply to Eli…"; on a phone, the sheet "Reply to Eli");
  - the drawing's sheet ("Draw your reply");
  - signed out ("you can reply to…");
  - the muted line ("Someone you muted replied.");
  - Activity ("replied to your comment", "replied with a drawing").

  Today's words are in `social/templates/social/_comments.html`,
  `social/static/comments.js` and `social/templates/social/activity.html`.
- **Icons alone on a phone** ("no need to show the words on a phone"). On a
  desk, "Reply" is spelled out beside its icon. Every button stays a 44px
  tap.
- **Two levels, then "Read more".** (The owner turned this to one level,
  everywhere, at the step 1 answers, before it was built: "Built: step 1",
  below.) A comment, its replies, and replies to those: that is as deep as
  a thread goes. Each level costs 48px of the
  words' room: 322, 274 and 226px on a phone, 292, 244 and 196px on a desk.
  It never gets less, however long the talk goes. Under a second-level
  reply whose talk goes on, "⊕ Read N more replies" sits on the thread's
  line: the row's second ink (`--ink-2`) with an 18px circled plus, a 44px
  tap, 7.1:1 light, 10.1:1 dark. N counts every reply under it, at any
  depth, that the viewer may see.
- **A reply's own page.** "Read more" opens the page of the reply it sits
  under, and the reply becomes the post, as on Bluesky. The header says
  "Reply", and back goes where you were. The page, top to bottom:
  1. The way to the reply, small and joined by the line: the post (or the
     drawing), the comment, and each reply on the way.
  2. The reply itself, as big as a post: its 48px face, its words, its full
     time, and its row with its counts.
  3. "Replies" with its count, then its replies, two levels again, each
     deeper branch with its own "Read more".

  Every comment and reply has such a page, so any of them can be linked and
  shared.

**Drawings in a thread: mock first.** The owner, at the yes: "not sure how
you'll handle drawings in there". A drawn reply (section 10's: 150px wide in
its own shape, with the player's line under it, fetched only when tapped)
is not in the mocks. The plan to mock, before anything is built:
- **In the thread:** the drawing sits inside its bubble under the words,
  still 150px. That fits even at the second level (226px on a phone, 196px
  on a desk).
- **On a reply's own page:** a drawn reply is the post, its drawing as big
  as a post's (on a desk, on the drawing's side).
- **In the way to it above:** a drawn comment shows a small still picture
  beside its words.

The same mock asks three smaller questions the build needs, each with a
default:
- **Deleting a reply that has replies.** Today a comment goes with its
  answers; the alternative is a "deleted" place that keeps the others'
  words.
- **What Copy link gives.** The default is the comment's own page.
- **The header on a top-level comment's own page.** The default is
  "Comment".

**The build, in three steps.** Each step is its own PR, with checks that
read its paint against its tokens in light and dark, shown red on today's
look before they pass. Each step shows only what works: no button waits on
a later step.

1. **The thread and its pages.** Bubbles, initials, the count pill, the
   lines, "Reply" everywhere, two levels, "Read more", a reply's own page,
   and the row with Reply and ⋯ (Copy link, Share…, Report or Delete).
   The data changes too. Today a reply to a reply is filed under the first
   comment (`parent_id` is always a top-level comment's; section 10), so a
   reply has to start keeping the reply it answers. That is a new column,
   empty for the replies already there, which stay at the first level, as
   now.
2. **Likes on comments**, counted, and shown in Activity.
3. **Repost and bookmark a comment.** A reposted comment shows as a card
   that opens that comment.

**Where it lives.** The site only: comments are the site's, so Pad and Flip
don't change (not for Flip: Flip has no comments of its own). Both pages
that carry comments get it: a post's and a drawing's shown outside a post
(`/social/b/<id>`). `harness/verify_socialcomments.py` is the suite it
extends.

**What Bluesky does**, from its code (github.com/bluesky-social/social-app),
read for the mock:
- **Two views.** The default follows one chain of replies, up to 10 deep
  (`LINEAR_VIEW_BELOW`). "Tree" view, the one in the owner's screenshot,
  shows every branch: 4 levels on a phone and 6 on a desk (`TREE_VIEW_BELOW`,
  `TREE_VIEW_BELOW_DESKTOP`). Its faces are 24px, where the chain view's are
  42px, and its lines are 2px.
- **"Read N more replies"** (`ThreadItemReadMore`, a circled plus) sits under
  the last reply a branch shows. It links to that reply's own post page,
  where the reply is the post with its replies below.
- **Lines end where a branch ends.**

Ours keeps our 36px faces and our bubbles, and stops at two levels, so the
words never squeeze.

**The four.**
- **Kind:** no conversation gets lost or squeezed, and a good reply can get
  a heart.
- **Simple:** two levels, then "Read more"; a reply works just like a post.
- **Powerful:** any reply, however deep, has a page of its own to link and
  share.
- **Playful:** following a conversation down is a tap, not a squint.

**Built: step 1, the thread and its pages** (Nov 17; DECISIONS.md, "The
comment thread, step 1"). What the yes said, as above, but for its two
levels; what the drawings mock ([Drawings in the
Thread](https://claude.ai/artifact/BsQKU7AnAeDfAxxGNXCJyc), Nov 17) asked
and the owner answered ("All yes", "Yes to all": each as the mock picked);
then, at that answer, ONE LEVEL, EVERYWHERE, in place of the two levels:
"We don't want the whole tree visible until someone selects the reply. It
just shows replies then if reply is clicked you see all the subs", and,
after [The Folded Thread](https://claude.ai/artifact/3mefzDKSCqWZ2PuSFMhTVZ)
mock, "What I want is a list of direct replies first. If you click the
reply it opens up the tree level", "Yes, build it"; and what the build
decided where all of them were silent:

- **The data.** On `social_comments` (migration `3b76663f9417`):
  `answers_id`, the comment or reply a reply answers, at any depth, with its
  index (`ix_social_comments_answers_created`) and a foreign key; `gone`, a
  place's "deleted" or "removed"; `person_id` may be nothing now (a place is
  nobody's), and a CHECK says a comment is somebody's or a place.
  `parent_id` stays the top-level comment a conversation hangs under, so a
  page reads a whole conversation by one index. The replies already there
  keep an empty `answers_id` and answer their comment: no data work in the
  migration (v309's lesson), the first level, as before. Going down refuses
  while a place is there.
- **One level, everywhere** (`comments.thread`, `replies_of`, `_fold`): a
  list shows only the direct replies to what its page is about, a post's or
  a drawing's comments (newest first), a comment's replies (oldest first),
  each alone in its bubble with nothing nested under it. One with replies
  under it carries "⊕ Read N replies" on the thread's line (N every reply
  under it, at any depth, that the viewer may see), which opens its own
  page, as a tap on its bubble does (not on a link, a button or its
  drawing, which plays; on a desk a pointer says so). Since Nov 18 the
  count stands by its talk cloud and each conversation is followed down
  under its comment ("Built: Bluesky's way, our look", below). Every reply in a list
  has a comment's room, 322px on a phone, 292 on a desk. A reply under one
  hidden from the viewer (a block, a takedown) is hidden with it, at any
  depth: not shown, not counted (`counts()` is a recursive read, one per
  kind, each step on the reply's own index), not a row in Activity
  (`chain_shown`).
- **Every comment's own page** (`/social/c/<id>`, `comment.html`): the way
  to it (`the_way`), it as big as a post and marked as the one you opened
  (below), then its own direct replies, all of them (no Load more), "Replies
  to Eli" and how many (every reply under it, at any depth). The header says "Comment" for a comment on the post and
  "Reply" for a reply. Back is the browser's own when you came from this
  site, else what it is on. A comment hidden from the viewer, or anything on
  the way to it, is a kind 404.
- **Replying.** A reply to one in a list is on that one's own page, so it
  joins its "Read N replies", which counts it and glows a moment (focus on
  it; since Nov 18, its count by the talk cloud, below). On a comment's own page the box replies to that comment, and a new
  reply lands last in its list.
- **Links land where a comment shows** (`comments.landing`): a comment on
  its post's or drawing's page, a reply on the page of what it answers,
  `#c-<id>` glowing there (Activity, Your Reports).
- **The row** in step 1 is Reply and ⋯ ("This comment": Copy link and
  Share…, both the comment's own page, then Delete comment, or Remove from
  my post and Report this comment). The heart is step 2's, Repost and
  Bookmark step 3's.
- **Drawings in a thread.** In a list a drawing sits in its bubble under
  the words, as wide as the bubble, which takes the whole room (the drawing
  294px wide on a phone, 264 on a desk), in its own shape, still, played
  only when tapped. On a drawn comment's own page its drawing is a post's
  (the whole width on a phone, the drawing's side on a desk), playing by
  itself as a post's does. On the way to a comment, a drawn one shows a
  small still beside its words (`comments.still`, the drawing's own still).
- **Deleting a comment or reply with replies under it keeps its place**
  (`comments.retire`): its words, its drawing, its mentions and whose it
  was go, and a quiet row stays, nobody's, a ring where the face was and
  "This reply was deleted" ("This comment…"; "…removed" when the post's or
  the drawing's author took it off), its "Read N replies" with it, so the
  replies under it stay where they are, at every depth. A place with nothing
  left under it goes, and so on up the way; one with nothing under it the
  viewer may see is not shown, and a place is never counted. It has a page
  of its own (the place as its head, its replies listed under it), nothing
  to reply to and nothing in a ⋯. In a list the place glides in where the
  comment was (`becomePlace`).
  Deleting an account does the same for each of its comments with somebody
  else's replies under it.

`harness/verify_socialcomments.py` sections 38 to 46 hold it; sections 3,
4, 5, 7, 9, 13, 16, 21, 22, 23, 25, 27, 28, 32, 33, 34, 36 and 37 moved to
its words, its one level and its places.

**Built: step 2, likes on comments** (Nov 17; DECISIONS.md, "The comment
thread, step 2"). The yes showed the heart in every comment's row; nothing
new to mock:

- **The heart** in every comment's row, in a list and on a comment's own
  page, between Reply and ⋯ (step 3's Repost will come before it): the
  post's own heart (`_comments.html` `comment_heart`, `likes.js`), its
  count beside it, none at zero, 44px. A like on a comment keeps no moment:
  `likes.js` reads no player for a heart in a comment, so the post's line
  gets no dot from it.
- **The data.** `social_likes.comment_id` (migration `5beec18dc5fe`), its
  foreign key, two indexes (once a person a comment; a comment's likes
  newest first) and the CHECK widened to a post, a drawing or a comment,
  exactly one (on PostgreSQL added NOT VALID). `owner_id` is the comment's
  author. No data work; going down refuses while a like on a comment is
  there.
- **Who may** (`/social/c/<id>/like`): as on a post, on a comment the person
  may see (`comments.seen`), not taken down and not a place. Counted by the
  viewer (`likes.stats`, a third kind), nobody hidden from them.
- **Activity**: the comment's author is told, "Mira liked your comment",
  "Mira and 2 others liked your comment", grouped as a post's likes, their
  comment's words under it, the small picture of its drawing, else of what
  it is on, opening the comment where it shows; quiet for the muted, never
  the bell's dot.
- **Deleting is said in code**: a comment that goes takes its likes, and so
  does one that keeps its place (a place is nobody's, nothing to like); a
  post, a drawing or an account takes its comments' with them.
- **Not in step 2**: who liked a comment is nobody's page to list (no
  "Liked by" on a comment), and your profile's Likes tab stays posts.

`harness/verify_sociallikes.py` section 16 holds it, section 11 its data;
`verify_socialauth.py` pins its PostgreSQL DDL.

**Built: step 3, repost, quote and bookmark a comment** (Nov 17;
DECISIONS.md, "The comment thread, step 3"), from the owner's "All yes" to
A Comment Shared (A, and quoting):

- **The row** under every comment, in a list and on its own page, is Reply ·
  Repost · the heart · ⋯. The repost is the post's (`_post.html` `repost`,
  `posts.js`): how many reposts and quotes, none at zero, lit in
  `--accent-ink` once yours; a tap raises the post's own sheet, Repost (or
  Undo repost) and Quote; signed out "Repost this comment?". None on a place,
  on one taken down, or on anything taken down on the way to it.
- **The ⋯ has Bookmark first** ("This comment": Bookmark, Copy link,
  Share…, then Delete comment, or Remove from my post and Report this
  comment): "Bookmark", then "Remove bookmark" once kept, with the post's
  toast and Undo (`posts.js` `window.SocialMark`, which `comments.js`
  calls); signed out "Bookmark this comment?". Nobody is told and nothing is
  counted, as a post's.
- **A comment out in the world** (A): reposted on Home's Following and the
  reposter's Posts tab, or kept in Bookmarks, it is a card of a post's
  shape (`_post.html` `comment_card`, `comments.world_cards`): "Ana Reyes
  reposted" at its top (a repost's), then THE WAY TO IT as on its own page
  (`_comments.html` `the_way`: what it is on with its drawing's still, then
  each comment it answers), its faces centred in the card's 44px column so
  the thread's line runs straight down into the card's face and meets it at
  its edge; then its face, name, @handle and when, its words, its drawing as
  a post's card's (its line waiting for the first play), and the post's row:
  its replies (every one under it the viewer may see), repost, heart, ⋯
  ("This comment", the post's sheet with a comment's words and routes:
  Report into the queue as a comment, Delete at once and the card folds
  away) and Open ›, its own page, which a tap on its ground opens too.
  Home reads posts' and comments' reposts in one query
  (`reposts.reposts_before`), the same comment twice in a page once, the
  newest; Everyone holds posts only. A comment's card is drawn only while
  its page would show it to the viewer (`comments.seen`): nobody hidden on
  the way to it, nothing taken down, never a place.
- **Quoting a comment**: the composer's Quote (`quote_comment`), the quote's
  small card the post's (`_gallery.html` `quote_card`) with "On Ben’s post"
  under its name (`.qt-on`, the second ink), one link to its own page, a
  drawn one's still; once it is gone or hidden from the viewer, "This
  comment is gone." A quote of a comment that went keeps
  `quoted_comment_id` 0 (`reposts.GONE_COMMENT`, no comment is 0), so it
  still says what it quoted; the column has no foreign key (a cycle the
  host's `create_all` cannot sort, and SQLite may give a deleted comment's
  id to the next), and every way a comment goes lets go of it in code.
- **Who may** (`/social/c/<id>/repost`, `/social/c/<id>/bookmark`, and for
  the composer's small card `/social/c/<id>/quoted`): as a post's, on a
  comment the person may see, nothing taken down on the way, no place
  (`reposts.comment_open`); once a person; your own; undone whatever became
  of it.
- **Activity tells the comment's author**: "Ana and 2 others reposted your
  comment" (grouped as a post's reposts, its words under it, opening it
  where it shows) and "Cyd quoted your comment" (the quote's words, opening
  the quote); never the bell's dot, nor a dot fading on Activity's own page
  (`activity.QUIET_KINDS`); quiet for the muted.
- **The data** (migration `36a8b352b347`): `social_reposts.comment_id` (its
  foreign key, `post_id` let be nothing, a post or a comment exactly one,
  once a person a comment, a comment's index); `social_posts.quoted_comment_id`
  and its index, the quote CHECK widened to a post, a drawing or a comment,
  at most one; `social_bookmarks.comment_id` (its foreign key, a post, a
  drawing or a comment exactly one, once a person a comment, a comment's
  index). CHECKs NOT VALID on PostgreSQL; no data work; going down refuses
  while a comment's repost, bookmark or quote is there.
- **Deleting is said in code**: a comment that goes, or keeps its place,
  takes its reposts and bookmarks and lets go of its quotes
  (`comments.retire`, `comments._drop`); an account its own reposts and
  bookmarks too (`reposts.drop_person_reposts`).

`harness/verify_socialreposts.py` sections 14 to 20 hold it;
`verify_socialauth.py` pins its PostgreSQL DDL.

**Built: Bluesky's way, our look** (Nov 18; DECISIONS.md, "The comment
thread, Bluesky's way"). The owner, Nov 18: "I want the replies to be
normal. Comment cloud shows how many replies. Click replies and replies
under that reply open up in the tree (nested) two deep". That tree was
mocked ([The Tree, Two Deep](https://claude.ai/artifact/Cq2iv1vL8sjSjPDTWDgcWV),
"Yes on all"), built, filmed and tried on a page of its own. The owner
then: "the tree thing gets weird with too many replies", "I want to go back
to the standard reply structure that bluesky uses, but with our look", and,
after Bluesky's own thread code was read (below), "yes, build it the
Bluesky way but keep our look for separation ... there won't be any of the
tree structure right?" Tried before it merged on [Bluesky's Way,
Ours](https://claude.ai/artifact/77WAuRNwDwVr3vKYFa5xCD).

**What Bluesky's default is**, read from its code (social-app, Nov 18):
its post page uses the linear view (the tree is an opt-in "lab" setting),
sorted "top". The post's direct replies are all listed. Under each, one
conversation is followed down: its top reply, the top reply to that, ten
deep (`LINEAR_VIEW_BELOW = 10`, `LINEAR_VIEW_BF = 1`), in the same column,
the avatars joined by a line. Where that chain stops with more under its
last, "Read N more replies" opens that one's own page. A reply's other
replies show only in its count, and tapping any reply opens its own page.

**Ours:**
- **The count by the talk cloud** says how many replies are under a
  comment, at any depth, that the viewer may see (`_fold`'s `more`). On a
  desk it takes the word Reply's place; a comment with none still says
  Reply. Reply still opens the box. Signed out, the count stands alone. A
  screen reader hears "Reply, 5 replies".
- **Each conversation followed down** (`comments._chains`): under each
  comment in a list, on a post's page and on a comment's own, its first
  reply (the oldest, so it reads as a conversation; we don't rank), the
  first reply to that, ten deep. All of it is in one column: our bubbles,
  every face the comment's, nothing stepping in. A drawing keeps its full
  width at every depth: 322px of room on a phone, 292 on a desk. A place
  (a deleted reply with replies under it) is walked through, as it is
  counted.
- **The line** is ours: 2px of `--card-edge`, straight down from face to
  face, into each face from the top of its room, never curving.
- **"⊕ Read N more replies"** (Bluesky's own words) where a conversation
  runs past ten: its circled plus on the line, a 44px tap, to the tenth's
  own page.
- **A tap on a comment opens its own page**, as before the tree.
- **Replying.** A reply continues a conversation where it is followed down
  to the one it answers, and that one had none: it lands right under it,
  glowing. Anywhere else the count by that one's talk cloud takes it and
  glows. Posting and deleting answer every count on the way up
  (`comments.tally`), so no count goes stale.
- **Pad and Flip** don't change: comments are the site's.

`harness/verify_socialcomments.py` section 47 holds it; sections 3, 5, 21,
32, 33, 39, 40, 41, 43 and 46 moved to the counts and the conversations,
and so did `verify_composer.py` and `verify_socialmute.py`.

**Built: the comment you opened** (Nov 18; DECISIONS.md, "The comment you
opened"). The owner, of a reply's own page: "it doesn't really let me know
that's the reply I'm seeing the replies for ... I don't want to make
another bubble... but something right?" Mocked as [The Opened
Comment](https://claude.ai/artifact/XeEzEbnyhN9eRPbJNN1yTr): A (a ring and
the name), B (a band and the name), and C, the owner's own "b with A's
ring too": "Yes to c". On a comment's own page:
- **The band**: the highlight's lilac at 70% over the page, from 12px over
  its face to 4px under its time, 14px past its column each side, rounded
  20px; no edge and no lift, so it is not a bubble. It was built solid
  (`--tint`, the token every highlight wears since No dinge); shown both,
  the owner picked the mock's softer one (Nov 18: "I like above
  screenshot"): 1.13:1 off the page in light, 1.26 in dark.
- **The ring**: 2px of `--accent-ink`, 3px round its face, as Skribl says
  "you are here" round your own; it also outlines a face that is an initial
  on lilac, which the band would swallow. A place has no face, and keeps its
  own empty ring.
- **"Replies to Eli"**: the heading under it says whose replies follow; a
  place's says Replies, a post's page Comments.
- **How**: the band is the page's own `::before`, laid in the grid's rows
  (`social.css`, THE COMMENT YOU OPENED), so no part moves into a box of its
  own and the scripts that reach the parts as the page's children don't
  change. On a desk with a drawing, the drawing keeps its column beside
  every row, and the band is in the words' column. The replies' row is the
  one that grows, so a drawing taller than the words' column stretches
  nothing in the band.
- **The way's line stops at the band's top edge** (the owner, Nov 18, from
  their phone: "The line should not go all the way to avatar, just to
  purple square edge above"): it never crosses the band to the face.

Section 48 of `verify_socialcomments.py` holds it, read off the paint.

## 19. Built: push notifications (nudges)

The owner, Nov 18, asked what other things a typical social site has that
Blooby doesn't; push notifications came first, and the mock, [Blooby's
Nudges](https://claude.ai/artifact/JmZrCBievKeNREBNAyzMTk), asked four
things. The answer was "All yes": A, the dot's rule; A, a card in Activity,
asked once; a Settings card with a switch a kind; the number on the icon,
on; the words as shown. `social/push.py`, `social/static/push.js` and
`push-sw.js`:

    /social/sw.js               the service worker: shows a nudge, the number
    /social/push/subscribe      this device may be nudged
    /social/push/state          what this device is nudged for, if anything
    /social/push/prefs          one of its switches
    /social/push/test           a nudge to this device now, and the answer
    /social/push/unsubscribe    this device, no longer

**What buzzes is what lights the bell's dot**: a reply to you, something
said on your post or a drawing of yours, a mention. Likes, follows,
reposts and quotes wait in Activity, unless a device's own switch says
otherwise. **A nudge is Activity's row, word for word**: after something
happens to somebody, their Activity is read as their page reads it, and the
newest new row of that kind is the nudge (`activity.sentence`, the words
`activity.SAYS` that the page shows too: "Ana replied to your comment",
"Mira and 2 others said something on your post"), with their words under it
in quotes, or a drawn reply's "Tap to watch it draw.", and a tap opens the
row's own link, where the comment glows. So whatever Activity leaves out (a
block either way, a takedown, somebody muted, a comment deleted meanwhile)
never buzzes either. Several on one post keep one tag, so the phone puts
the newest in the place of the last, and one Topic, so a phone that was off
is handed the newest only. A device is never told about a row older than
the newest it was told about, so something that makes no row of its own (a
muted person's comment) cannot buzz the row before it again.

**When it is sent.** The host commits a request's work once, at its end;
who should hear about it is noted on the session as the work is done
(`push.note`, from the places that write a comment, a mention, a like, a
follow, a repost and a quote), and only a commit that went through sends
anything, from two threads of the process's own, so a reply never waits on
Apple or Google and a request that failed tells nobody. The sending reads,
then lets go of the database (on SQLite a read holds the file's lock), then
talks to the push service, then writes what it learned.

**Where it may go.** Only to the push services browsers use (Apple's,
Google's, Mozilla's, Microsoft's), over https, never following a redirect:
nobody can make the site send to an address of their choosing. A push
service that says a device is gone (404 or 410) takes it away.

**Sealed and signed.** Each nudge is sealed for its device alone (RFC 8291,
aes128gcm; `verify_socialpush` holds it to the RFC's own worked example,
byte for byte) and signed as the site (VAPID, RFC 8292), with the
`cryptography` package the passkeys already brought: nothing new to
install. The signing key is the deployment's `SOCIAL_VAPID_KEY` where it
sets one (a PEM, or 32 bytes in base64url), else made from its
`SECRET_KEY`, the same every time for the same secret: nothing new to keep.
A new `SECRET_KEY` is a new key: the old devices go as their push services
refuse them, and each is made again the next time its person turns nudges
on. Push services charge nothing.

**It lives with the sign-in** (`social_push_subscriptions`, on the site's
own chain). Signing out here takes this browser's devices; Sign out
everywhere takes them all (and a device from before it is never nudged);
deleting the account takes them, in code. A device somebody else signs in
on stops being nudged for the one before: each new sign-in's pages ask
`/push/state` once (push.js keeps a mark of the sign-in, never the
person's), and a device kept for anybody else is let go. Somebody who turns
nudges on there takes it, starting at the dot's rule again. Ten devices a
person at most; the oldest goes.

**Asked once, in Activity** (A). A card under Activity's heading: Blooby's
Home Screen icon, "Hear when someone answers you", what buzzes and what
waits "on this phone" (tablet, computer: this device's word), Not now and
Turn on. It shows only where this device can be nudged, was never told no,
is not nudged already, and nobody said Not now on it. Not now puts it away
for good on this device; Turn on asks the browser from the tap (an iPhone
asks only then), and the card goes. It glides open over the list and away
again (the comments' fold); under Reduce Motion it is put there and taken
away at once. Opening Activity also clears the number on the icon and the
nudges already shown: everything in them is seen.

**Settings: you choose each kind.** "Notifications on this phone" under
Theme, "What may nudge you when Blooby isn't open.", then a row a kind with
Theme's own switch (On, Off): Replies and comments, Mentions, Likes, New
followers, Reposts and quotes, and The number on the icon, the dot's rule
pressed. The choices are this device's, as the permission is. Before it is
on, the card offers Turn on; told no, it says to allow notifications for
the site in the browser's settings; an iPhone or an iPad in a browser tab,
where no web page is nudged, is told that nudges come to Blooby on the
Home Screen, with Add to Home Screen (the ☰'s own steps); a browser that
cannot, says so. A switch moves at once; one the site did not take goes
back, and says so. The rows' thin line is the passkeys' (`--rule`), a shade
softer than the mock's.

**The number on the icon** is how many new things light the dot, set by
the service worker as each nudge arrives (where its switch is on), and
cleared by opening Activity.

**Send me a test nudge** (the owner's yes, Nov 18, after testing with their
own likes, which never nudge you): a button under the switches. It sends one
nudge to this device at once, "Hello from Blooby", "Nudges work on this
phone." (tablet, computer: push.js's word for the device), a tap opening
Settings, where it was sent from, never Activity, which has nothing of it
(the owner, after the first one on their iPhone: "it doesn't show in
activity"); `/push/test`. The line under the button says what the
device's push service answered, by name: "Sent, and Apple took it. Look in
your notifications.", or "It didn't go through: Apple answered 403,
BadJwtToken." with the service's own word, so a phone can be checked alone
and a refusal is never silent. A device its service says is gone is let
go, and the card offers Turn on again. Twenty an hour a person. A refusal of
a real nudge goes to the server's log, with the service's own word.

**Not tested here**: a real push service and a real phone. The suite's
stand-in push service is handed exactly what Apple's or Google's would be,
opens each nudge with the device's own keys and checks its signature; the
service worker is the real one, handed pushes through Chromium's own
DevTools. Nudges travel only from the live site; an iPhone needs Blooby on
its Home Screen. `verify_socialpush.py` holds the rest.


## 20. Built: Draw back, step 1

From the Draw back mock and the owner's "All yes", Nov 19 (DECISIONS.md,
"Draw back, mocked", which holds the eight choices). The one new verb:
answering a drawing by drawing with it. `social/drawback.py`, `posts.py`:

    /social/p/<public_id>/drawback    GET: the drawing to lay under the pen
                                      ({payload, first}), for the composer;
                                      open to you as a like asks, and one
                                      that can be drawn back on
    /social/posts                     POST with {draw_back: a post's
                                      address, payload: the answer's
                                      strokes}: the server joins the two

THE PEN after the heart under a post's drawing (one page), signed in, with
how many draw-backs. It opens the composer, which says "Drawing
back on Ana’s" at its top, and the Pad over it with her drawing faint under
the pen on her shape and paper (Skribl's `lib/drawback.js`, handed over by
`lib/composehost.js` underlay). THE SERVER JOINS THE TWO from her drawing as
Skribl stores it (`skribl.read_payload`): hers first as it plays, squeezed
to three seconds when longer, then his at his own pace. A draw-back is a
post (`is_drawback`, `drawn_on_id`, `drawn_on_owner_id`); its card says
"Drew back on Ana’s", her face small at the foot of his.

STEP 2 (DECISIONS.md, "Draw back, step 2"): Activity's "Theo drew back on
your drawing", the dot and the nudge (Replies); her post's strip of
draw-backs, newest first; and "Watch again" and Draw back rising at a
drawing's foot when its replay ends (Skribl's player says `skribl:ended`).

NO PEN WHERE IT CAN'T BE DONE YET (DECISIONS.md, "Draw back: no pen where it
can't be done yet"): a Flip of pages or a drawing with recolours, read when
its post is made (`undrawable`); a post from before keeps its pen, answered
when opened.

THE AUTHOR'S BACKGROUND AND MUSIC (DECISIONS.md, "Draw back: your own
drawing, and the author's background and music"): a draw-back keeps her
paper, her photo and her song, and the answer adds none of its own (refused
with why). The Pad shows her photo under the pen, the composer's preview and
the picture the post rests on show it, and her song plays under both. Where
Skribl keeps media in a store, the site reads hers back as data
(`skribl.read_payload(..., inline_media=True)`); the store keeps content
once, so the draw-back costs no more room.

WHAT IT SAYS OF ITSELF (DECISIONS.md, "What a draw-back says"; section 21,
choice 6): each hand's own drawing time is kept when it is made
(`social_posts.hands_json`), its line says them ("Drawn in 15 sec + 5 sec"),
its play button who and the whole ("Ana + Theo · 20 sec"), a Gallery tile
and a quote the whole. Nobody is named to a viewer any of them is hidden
from, nor once the drawing it answers is gone.

STILL TO COME, in the decided order: her say (hide one from her post; who
can draw back); drawing back on a Flip, page for page; recolours.
`verify_socialdrawback.py` holds what is built.

---

## 21. Built: the walkthrough's mocks (the owner's "all yes", Nov 19)

A walkthrough of the site on a fresh copy (five made-up people, eleven
posts) put ten choices to the owner as a mock page
(https://claude.ai/artifact/MxPYZyHAtdR4hEg9YiXAuR), each with today beside
it; DECISIONS.md, "One repository (the owner's yes to A), and the
walkthrough's six mocks", lists them. "All yes." What each one built is said
where it lives above; this is the index.

- **1 and 2, inside a post:** the editors' menu has no Library and no Public
  gallery while composing, and the site's composer asks for no gallery tick
  ("A post is a drawing and words", above; docs/INTEGRATION.md).
- **3, "Draw back" in words:** on a post's own page the draw-backs' line
  ends in the words, the site's second button with the pen, there from the
  start ("No draw-backs yet") wherever the pen is offered; the row of
  buttons above it is not touched. (Since the Calm Post Page, Nov 20,
  section 23: the words are the answer bar's, and with nothing drawn back
  there is no line.)
- **4, a drawn comment:** at rest no taller than its page's own drawing (156
  by 277 under a post's 370 by 278 on a phone, where it stood 294 by 523),
  its line waiting and its play button the card's glass pill at its foot; a
  tap plays it and it grows to its room, gliding, and stays; one drawn wide
  is in its room from the start; under Reduce Motion it plays where it
  sits. Section 18's "as wide as the bubble, with its line" is what it
  grows to.
- **5, the thread:** 30px before a new conversation, 12 inside one (it was 12
  everywhere).
- **8, the repost sheet:** Quote wears a pair of quote marks of its own; the
  pen says Make, Draw back and Edit drawing.
- **9, faces:** one not drawn yet shows its initial on a post's card, a
  post's own page and in Activity (16px in a card's 44px disc, 19 in a
  page's 48, 11 in the small face at the foot of a draw-back's), in the
  small violet ink on the site's disc. A Gallery tile's 22px face stays
  plain. Lists of people (followers, who liked it, search, the blocked) are
  as they were: not in the mock, the owner's to say. Two faces sharing a
  row of Activity ("Juno and 3 others liked your post") stay plain too:
  they overlap, and a letter there was cut, the one behind by the face in
  front and a wide one in front by the heart (found taking the pictures of
  what was built; the mock showed rows of one face).
- **10, the Gallery's head:** Following | Everyone and New | Hot share one
  line, 8px apart, and the search box takes the next line whole, so
  "Search people and drawings" fits a 402px phone (217px of words in 304;
  it had 178). Signed out, New | Hot has the line.
- **6, what a draw-back says:** its line each hand's own time ("Drawn in 15
  sec + 5 sec · watching at 1×"; past three parts, the whole and how many
  people), its play button who and the whole ("Ana + Theo · 20 sec"; past
  four names, "Ana + 4 others"; the time alone where the drawing is too
  narrow), a Gallery tile and a quote's small card the whole. It said
  "drawn in 8 sec" under a cat that took 15. Kept on the post when it is
  made; one from before is said from the two drawings' own lines while its
  original is there. Skribl's player is handed the numbers (docs/INTEGRATION.md,
  "A drawing of several hands") and knows nothing of who.
- **7, loop:** Skribl's players draw the infinity sign for loop (the in-post
  player, the link page's, the Library's, the full-screen bar, the Pad's
  Repeat and Export's looping GIF: one picture by `verify_icons`). On the
  site it sat 38px above repost's two arrows in a ring, the same picture.
  Flip's "Loop this page" and the music drawer's loop keep the arrows:
  other verbs.

## 22. Built: the evening's six (the owner's "All yes", Nov 19, about 7:40 PM)

The page put to the owner that evening had four parts and six choices
(`DECISIONS.md`, "Yes to all to the seven ... the evening's mocks"); "All
yes" took the default of each. Built in four pull requests, each with its
entry in `DECISIONS.md` and its checks shown red first.

- **6, the pencil's line:** the little wave the pen draws in the Draw back
  icon wears `--brand`, the pen's line under the chosen tab; the pen stays
  in the ink of where it sits. One macro, so the row under a post, the
  draw-backs' title, "Draw back" in words and Activity's badge change
  together; on the pill that rises when a replay ends (the action's fill)
  the wave stays white (`verify_socialdrawback` 9).
- **4, a draft's tile on your profile:** a tap opens the draft inside a
  post (the composer's sheet with the editor that made it over it, the
  sheet not painted until Add), where it was a link out of the site to the
  editor by itself. Put away without Add, the sheet goes with it and you
  are on your drafts (`compose.js` `SocialComposer.draft`;
  `verify_socialprofile` 20).
- **5, a posted draft:** stays in Drafts, as it did. Nothing built.
- **1, Your hand inside a post:** the Text drawer's "Make yours" and "Edit
  your hand" open Your hand in a layer over the editor, which never leaves,
  where the composer's frame used to go there and come back as the editor
  by itself with the drawing gone. Skribl's own (`lib/handover.js`;
  `verify_text` 23, `verify_composer` 10); nothing of the site's changed.
- **2 and 3, How it works:** below.

### How it works, the site's own page (`how.py`, `how.html`, `how.js`)

The site had no door to any help: the ☰'s own note said "No Help row until
there is a Help page." Now `/social/how`, for anybody, signed in or not.

**Its doors.** The ☰'s first row on a phone (How it works, then Settings,
or Sign in for a visitor), and on a desk a tab in the rail above Settings
(above Sign in before that), lit on its own page as Home's is. A phone's
bar keeps its four places, and the page has no ☰ of its own.

**The page**, in the shape of the Pad's own How it works, so the two read as
one family: "How it works", "Blooby is where people talk in drawings.",
then three parts.

- *Watch an example.* Three drawings, each in Skribl's in-post player (the
  box a post has), 168px wide on a phone so the third shows there is more
  to the side: a drawing, a draw-back, a Flip. THEY ARE FILES, NOT POSTS, so
  they are there on a site with no posts yet: Skribl's cat and its bouncing
  Flip (its help's demos, named with `skribl_asset`), and the site's own
  draw-back (`static/how/drawback.json`): that cat, and a ball of yarn
  drawn on it with a real pen through the composer's Pad, joined as the
  site joins every draw-back. Each box keeps its drawing's shape before the
  drawing comes, so nothing moves; each play button says what its file says
  (the cat's 15 sec; the draw-back's two hands, 15 and 6, so 21; the
  Flip's 10 pages). The first draws itself once as the page opens, never
  under Reduce Motion; a tap plays one and stops another. If the files do
  not come, one line says so, with Try again.
- *People often ask.* Four rows, the question over its answer in the fewest
  words ("Post a drawing / The pencil, then Draw"), and a tap goes where it
  is done: the composer on this page; Home's Everyone, where the drawings
  are; your profile. A visitor reads the same four with nothing to tap, and
  one line says why ("You'll need an account for these, and Blooby is by
  invite for now."), Sign in beside it.
- *The drawing tools.* "The Pad" and "Flip", the editors' own How it works.
  Signed in, each opens that editor INSIDE A POST with its help showing
  (`SocialComposer.editor`, the same way in as a draft's tile: only the
  editor is seen, its × is back on this page, and Add starts a post with
  what was drawn), so nobody is sent out of the site to the editor by
  itself. Each is still a link to the editor's own address with `?help=1`,
  which is where a visitor goes: their only Pad is that page, as Make's two
  doors are.

**What it asked of Skribl** (docs/INTEGRATION.md, "Sending people to the
editor's own How it works"): the editors open their own How it works when
their address carries `?help=1` (the flag leaves the address), and when a
host's composer asks the editor it holds (`skribl:compose:help`). One
module for both editors (`lib/ask.js`).

`verify_socialapp` 11 holds the page and its doors, `verify_ask` 6 the
editors' side.

## 23. Built: the calm post page (the owner's "All yes to everything", Nov 20)

The owner, of a post nobody had answered: "It seems busy and disorganized.
When there are comments and drawbacks it looks better and makes sense ... I
don't want anything to ever look busy and confusing." Then, beside two
pictures of Bluesky: "Bluesky looks simpler. Most because there aren't the
more from images." And to the mock's five choices (the artifact "Calm Post
Page"): "All yes to everything. Make it smart and beautiful." That page had
three bold headings, two of them over nothing, seven things in violet, and
the same two actions offered three times each in three shapes.

**One answer bar** (`_comments.html` `answer_bar`; `social.css`, THE ANSWER
BAR), on every post's page, every drawing's and every comment's: your face,
a line that looks like a field and is a button, "Say something…" (a
comment's own page: "Reply to Eli…"), and Draw back where the post can be
drawn back on. It took the place of the round icon at a "Comments" heading's
end, of "Say the first thing", and of "Draw back" at the end of the
draw-backs' line. Nothing else on the page offers either in words; the row
of icons above is as it was.

- *A phone:* fixed at the foot of the screen, standing on the bottom bar,
  on the bar's own glass, 60px tall. The page keeps 60px more at its foot
  and the toast rises 60px higher there, so neither is ever under it. A tap
  on the line raises the box's sheet, as the icon did.
- *A desk:* in the column, 18px under the date, without the face. THE LINE
  BECOMES THE BOX: the two share one room, so the box glides open over the
  line while the line fades away under it; Esc or a press elsewhere folds
  it away and the line is back. What is under them moves by the
  difference, the box's room less the line's 44px.
- *The line is the site's card,* its ring and its lift, as a comment's
  bubble under it is. THE MOCK DREW IT WITH ITS RING ALONE, and in light
  that was a white box on near-white set apart by its line and nothing
  else (1.03:1 on a phone), which the owner ruled out on Nov 16 ("just a
  border"); `verify_socialreposts` 13 found it. The lift is the one thing
  built that the mock did not show.
- *Signed out,* the line is there by itself and raises "Say something?".
  A place (a deleted comment's own page) has no bar: it takes no reply.

**Small quiet labels** where bold headings stood: "3 draw-backs", "7
comments", and on a comment's own page "3 replies to Eli" (whose replies
follow: the owner's yes to C, Nov 18, kept), in the row's second ink, 15px
and semibold, each still a heading to a screen reader. AND NOTHING WHERE
THERE IS NOTHING TO LABEL: no draw-backs, no strip at all; no comments, no
label. The comments' label fades in with the first comment and goes with the
last, leaving once that comment's room has closed.

**No More from** on a post's page or a drawing's (`posts._post_page`; the
read behind it, `feed_page`'s one-person branch, went with it). Their face
and name open their page.

**When a replay ends** on the page (`posts.js`), Watch again rises alone on
the drawing and the bar's Draw back lights up in the action's own fill,
white on it, until it plays again: the invitation at the moment it is
wanted, said once. A card on Home keeps both pills, as before.

**The row's talk cloud** on a post's own page is a way down to the
comments. With none to go down to its own name is "Comment", and a tap on it
opens the box (`comments.js`), so it is never a tap that does nothing.

**Not changed:** Home, profiles, the comment sheet (it still opens ready to
type), the drawing's own bar and its "Drawn in… watching at 1×" line, which
are Skribl's player. The Pad and Flip: nothing of theirs.

**Measured as built** (a touch phone 402 wide, and a desk; light and dark):
the bar 402 by 60, its line 179 by 44 beside a Draw back of 139, 370 when it
is alone; "Say something…" 16px, 7.56:1 light and 8.59:1 dark; the labels
7.1:1 and 10.12:1; Draw back lit 5.33:1 in both. An empty post's page is
874px, one screen, where it ran 1117.

`verify_socialcomments` holds the bar, the box behind it and the labels
(sections 1, 12, 29 to 37, 40, 46, 48), `verify_socialdrawback` the bar's
Draw back, the strip and the replay's end (6, 7, 9), `verify_socialposts`
that More from is gone (3, 9). NOT TESTED HERE: Safari on an iPhone, where
the bar stands on the bottom bar above the home indicator and the keyboard
rises under the sheet; the owner's phone is the test.

## 24. Built: Her say, hiding a draw-back from your own post (Nov 20)

Approved on Nov 19 ("she may hide a draw-back from her post"), mocked on Nov
20 (the artifact "Her Say"), and answered that morning: "All yes to
everything." Four of its seven picks are this section; the other three (who
can draw back) are the next.

**The eye, on your own strip.** On your own post's page each draw-back's
tile wears the eye your Gallery tab has, the same button and the same two
drawings (`_gallery.html`'s, `eye.js`). It sits BESIDE THE NAME, never on the
picture: the tiles are 132px wide and what somebody drew back is often in a
corner. So your tile is 147px tall (the name's line is the eye's 44px) where
everyone else's stays 125. Here the chip is on the page, not on a drawing, so
it wears the second button's lilac with the eye in the small violet ink.

**One tap** hides that draw-back from your post. At once the eye crosses,
its chip says "Hidden", the drawing fades to 55%, and your page's own counts
follow: the label says what everyone else sees ("2 draw-backs"), one quiet
line under it says how many are hidden, yours alone ("1 hidden from your
post"), and the row's pen says one fewer. The site's toast says "Hidden. Sam
isn’t told." with Undo, never over an eye. The hidden one stays on your own
strip, faded, so you can find it: its eye brings it back any time ("Back on
your post.").

**For everyone else it is simply not on your post**: not in the strip, not
in its label, not in the pen's count, on your post's page and on Home's
card. With every one hidden nobody else has a strip there at all; you have
the one line and the faded tiles.

**Nothing else of it changes, and nobody is told.** It is still its maker's
post: on their page, on Home, on its own page, still saying "Drew back on
Ana’s" with the way to yours, still playing yours and then theirs. Its
maker sees it gone from your strip, as everyone does. No Activity row, no
dot, no nudge. Nothing is deleted.

**How it is kept:** the site's own flag on the draw-back
(`social_posts.drawn_on_hidden_at`, migration `a4c9e1b7d352`), set through
`/social/p/<its id>/shown` (`posts.drawback_shown`) with `{"shown": false}`.
Yours alone: the maker of the post it draws back on, with the page's token;
anybody else, its own maker among them, is answered 404, as is a post that
is no draw-back, one whose original is gone, and one taken down. `drawbacks()`
leaves it out of every count; the strip's read leaves it out for everybody
but you.

**Nobody else has any of it:** no eye, no hidden tile, no line, no `eye.js`,
no address to hide one, in the page or its source.

`verify_socialdrawback` 11 holds it. The Pad and Flip: nothing of theirs.
NOT TESTED HERE: Safari on an iPhone.

## 25. Built: Her say, who can draw back (Nov 20)

The other half of Her say, the same mock and the same answer ("All yes to
everything"): its choices 4 to 7. A post's maker says who can draw back on
it, post by post: **Everyone** (where every post starts), **People I
follow**, or **Nobody**.

**The one rule** (`posts.open_to`), read by everything below. Her own post
is always hers to draw back on, on Nobody too. Everyone is anybody signed
in. People I follow is whoever SHE follows now: unfollowed, their pen goes
(what they drew back before stays); following her lets nobody in. Nobody is
nobody else. Whether a drawing CAN be drawn back on is another question
(`drawback.drawable`), and so is whether somebody may see the post at all.

**Somebody who can't has no pen at all**, as on a Flip: none in the row (on
her post's page and on every card), no Draw back in the answer bar (its
line runs to the bar's end), nothing rising when a replay ends. Nothing
says why, and nothing about it is in their page or its source. The
draw-backs her post already has stay where they are, for everybody, with
their label.

**Both doors hold it.** The composer's way in (`/p/<id>/drawback`) and the
post itself (`posts._drawing_back`) each ask the rule again, so a page
opened before she closed it, or a draw-back begun before and posted after,
is refused: 403 `drawback_closed`, which the composer says as "That drawing
isn’t open for draw-backs right now."

**In her own post's ⋯:** a card of its own under the first, "Who can draw
back" with Draw back's pen, then SETTINGS' OWN PILL (`.theme-switch`; the
three choices each 44px tall and as wide as its words) and one line saying
what the choice means: "Anyone on Blooby can draw back on this.", "Only
people you follow can draw back on this.", "Nobody else can draw back on
this. The ones it has stay." A tap is the change, as in Settings: the tint
slides, the line changes, the site is told
(`/social/p/<id>/drawback-by`, `{"by": ...}`). If the site can't be told,
the pill goes back and the sheet says "That didn’t go through. Try again?".
Only there: not in the ⋯ of somebody else's post, of a Flip, or of words
alone. The same card is in the ⋯ of her post wherever it is a card (her own
page, Home), and every card of that post takes the choice.

**On her own post's page, one quiet line** while it is not Everyone: "Only
people you follow can draw back. Change" (or "Nobody else can draw back.
Change"), under the draw-backs' label; Change opens her ⋯ where the pill
is, and focus comes back to it. Where nobody has drawn back yet the line
stands alone under the date: on Nobody that is where it would stay, since
nobody else can make the first. At Everyone there is no line and it takes
no room.

**In the composer, under the drawing:** one quiet line, "Anyone can draw
back · Change", the whole line a button. Change opens the same pill where
the line stood, growing into its room (0.26s; a fade where it stands under
Reduce Motion), focus on the choice pressed. Post sends what is chosen
(`drawback_by`); left at Everyone nothing is sent. Put away and opened
again, the sheet shows the line again, saying the choice ("Nobody else can
draw back · Change"). A drawing removed takes its choice with it. The line
is there only while what is attached can be drawn back on, by the site's
own rule read in the page (`compose.js` `drawableHere`, held beside
`drawback.drawable` by the suite): a drawing from the Pad, an older drawing
from Yours, a draw-back (which is a post too); never a Flip, never words
alone.

**How it is kept:** `social_posts.drawback_by` (migration `c8d3f5a1e694`),
nothing for Everyone, `follow` or `nobody`; no data work, every post there
stays open. The pill outside Settings is placed by `social.js`'s
`SocialSwitch`; the words live in `_who.html` and nowhere else.

`verify_socialdrawback` 12 holds it (21 rows). The Pad and Flip: nothing of
theirs. NOT TESTED HERE: Safari on an iPhone.

## 26. Built: no strip of the page under a sheet on a phone's keyboard (Nov 20)

The owner's picture of the Make sheet on their iPhone showed Home between
the sheet's foot and the keyboard's own bar. The sheet rode above the
keyboard by being lifted whole, so its box ended where the keyboard began,
and what the keyboard's see-through bar uncovered was the page behind.

**Now the paper runs down behind the keyboard.** On a phone the sheet is
not lifted: a spacer the keyboard's height stands at its foot
(`.cmp-sheet::after`, from `--cmp-kb`, which `social.js`'s `SocialKeyboard`
keeps as before). What is in the sheet sits exactly where it sat, its tools
16px above the keyboard, and the sheet's own paper goes on to the screen's
foot. The small comment sheet does the same (`--cm-kb`). A desk's card
(900px and wider, a tablet with a keyboard on its screen among them) never
rode a keyboard and does not now: the spacer is a phone's alone.

Nothing else changes: the keyboard is read the same way, read again until
it rests, and a page that itself changed size takes the new reading at
once.

`verify_composer` 3 and `verify_socialcomments` 30 hold it on a stood-in
keyboard, by what is painted where the keyboard would be. NOT SEEN HERE:
this box has no phone keyboard; the owner's iPhone is the test.

## 27. Built: a screen's arrow goes where you were (Nov 20)

The owner: "there's no back button on so many screens. You end up stranded
a lot". Part one is the arrows the site has (a post's page, Activity, a
comment's own page). They are one rule now, in `social.js`:

- **The page you came from, when it is this site's**: the arrow
  (`a.top-back`) is the browser's own Back, so a post opened from the
  Gallery brings you back to the Gallery, from a profile to the profile,
  and Home opens where you had scrolled to.
- **Its own address otherwise** (a link somebody sent, a new tab, the app's
  first page): Home for a post and for Activity; for a comment's page, what
  it is on.

A phone's Home Screen app has no browser Back, so this arrow is the only
one there. It says "Back".

**Part two (the owner's "All yes" to the mock's A, the same evening): every
screen the bar does not lead to has the arrow**, at its top's start, with
the screen's name beside it, as a post's top: Settings, Edit profile,
Delete account, How it works, the three rules pages, an admin's Invites and
Reports, and somebody's profile (before their @name). The page's big
heading leaves a phone where the top says it (`.page-head.in-top`; a screen
reader's still, and a desk's). A door screen (Sign in, Join, Add a passkey)
keeps the mark in the middle and has the arrow at the top's start. Home,
the Gallery and your own profile have none: they are where the bar leads.
A desk shows no arrow anywhere.

**The mark's ink is in the middle, not only its link** (the owner, the same
evening: "blooby. Does not look centered, does it?"). The link is 76px wide
for a 61px mark, which stood at the link's start, 7.75px left of the
screen's middle; under 900px a door's link holds the mark in its own middle
now (`body.focus .top .brand`). A desk's door has the mark at the page's
start, as the rail does.

Opened with nothing behind you, each goes to the screen it belongs to:
Settings and Edit profile to your profile, Delete account to Settings, the
rest to Home (Join and Add a passkey to Sign in).

`verify_socialposts` 21 holds both parts, with `verify_socialcomments` 40.

## 28. Built: each row of a grid of tiles on one faint band (Nov 20)

The owner, of the Gallery in dark: "anything like this with rows should
maybe have slightly diff color under each [row]. Almost imperceptible but
enough so you can tell where top and bottom are.. each row distinct". A name
sits 8px under its own picture and 18px over the next row's, and a drawing
on dark paper has no edge on the dark page.

**Under every row, one flat band** (`.gal-grid > *::before`): the token
`--row-band` (the page's own colour stepped about one part in twelve, solid;
`--row-band-sheet` on a sheet's paper), 8px out past the grid, 7px over the
pictures, 8px under the names, the page showing between two rows. No line,
no blur. The row's own cells draw it, each to its share of the row; a last
row that is not full is still a whole band.

It is wherever the grid is: the Gallery, a profile's Gallery and Drafts
tabs (your own, where each tile sits in a cell with its eye), the front
door, and Make's "Use one you made".

`verify_socialposts` 22 holds it, read off the paint.

## 29. Built: crisp, three heights, and nothing soft at rest (Nov 20)

The owner: "I want to minimize shadows to create depth and keep it crisp
and luxurious. Shadows seem blurry and kind of muddy the page." Their "All
yes" to the crisp mock's B. Depth on the site is three heights now, and a
soft shadow (more than 2.5px of blur) is only for what floats:

- **On the page** (a post's card, a comment's bubble, a tile, a panel, the
  answer line, the comment box): the edge and one line of shade under it,
  1px with no blur (`--card-drop`). In dark, a line of light inside the top
  edge.
- **In a card** (the drawing in a post's card, a bubble or the comment
  box): the edge alone. A drawing on the page itself (a post's own page,
  How it works, the front door, a sheet's paper) keeps the page's line
  (`--draw-lift`).
- **Floating** (a toast, the list under an @): the one shadow, short and
  close (`--float-drop`). A sheet casts nothing and has a line of light
  along its top (`--sheet-top`). The play pill on a drawing has a hairline
  and 1px/2px (Skribl's `inlineplayer.css`, so wherever that player is).
- **The fill** (Make, Post, Follow, Draw back lit): enamel, no glow
  (`--fill-drop`).

**Before adding a shadow, count.** `verify_socialposts` 23 reads Home, a
post's page, the Gallery, a profile's grid and Settings, phone and desk,
light and dark, and holds the soft shadows at rest at none; it also
resolves every shadow `social.css` declares and lets only the two floating
rules be soft. A new surface gets an edge first; if it floats, it wears
`--float-drop`.

What sets a white card apart from the near-white page is its edge and that
one line (the "just a border" census, `verify_socialreposts` 13, counts the
line as the lift a soft shadow used to be).

## 30. Built: a wrong address is a kind page (Nov 21)

Owed from section 27's second part (the owner's "All yes" to the way
back's mock: "a kind page for a wrong address"). An address under the site
that nothing answers was the app's bare "Not Found": no bar, no way home,
nothing on it at all. It is the card a missing post has now (`lost.html`):
Blooby, "That page isn’t here", one line, **Back to Blooby**, and the bar.

- **A route of the site's own** (`/<path:rest>` under the site's prefix,
  every verb; `social.lost`, in `social/__init__.py`), not a handler on
  the app: whatever nothing else under the site's prefix answers lands
  there, so it is the site's request, with its person, its page's frame
  and its headers. A HOST THAT MOUNTS THE SITE SHOULD KNOW IT: every
  address under the prefix it gives the site is the site's to answer, and
  nothing outside that prefix is touched (the host keeps its own 404s and
  its own handler). The route reads nothing and does nothing.
- **A person going there gets the page; anything else gets what it got.**
  A browser's navigation says `text/html` by name, and gets the card
  (404). A script's fetch (`*/*`, JSON) and every other verb get the bare
  404, without the site's headers: word for word and header for header
  what an address outside the site gets.
- **A page the asker may not know is there is still not told from one that
  is not.** Invites and Your reports answer 404 to anyone but an admin.
  They are the same card now, with the same headers, as an address that
  was never one; and to a script the same bare answer (`_not_here`, the
  blueprint's one handler for a 404). `verify_socialauth` 6 lays the two
  side by side, a script's ask and a browser's.
- **What routing gives up for it:** an address the site has under another
  verb (a form's address gone to by hand, a page posted to) answered 405
  and answers 404 now, as a page that is not there. Gone to by a person,
  that is this card where it was a bare "Method Not Allowed".
- A view's own kind page (a post not there, nobody by that name) is as it
  was: those views answer for themselves.

`verify_socialposts` 21 holds the page (two rows: gone to, signed out and
signed in, a phone and a desk; and what a script reads).

## 31. Built: the person's tap stops at their name (Nov 21)

The owner: "on posts the name or icon should take you to profile but
anything on top right should open post. Right now profile tap extends past
name. It should stop at name so tap up there to right of name opens post."

Since "Easy to open" (Nov 12) the name's link on a card was a block as wide
as the card's whole top, 44px tall: 280px on a phone and 886 on a desk for
a name 73px wide. Everything to the right of a name went to the person.

- **The name's link is as wide as the name** (`.post-card .post-name`:
  `align-self: flex-start`), 44px at the least for a name of two letters,
  and still 44px tall, reaching down under the second line.
- **The @handle is a link of its own** to the person's page (`.post-at`),
  as wide as the @handle, its tap reaching down as the time's does. It was
  plain text that let a tap through to the name's link under it, which
  only worked while that link was as wide as the top. A second way to the
  same page, so it is out of the tab order and not read out, as the face's
  link is.
- **What is left of the top is the card's own ground**, which opens the
  post (`posts.js`): right of the name, the far end of the top, and right
  of the time on the second line.
- Nothing moves: the top, its second line and the time are where they were.

A post's card and a comment's card both (`_post.html`). A post's own page
and a comment's own page are not cards, and are as they were.

`verify_socialposts` 10 and 11 hold a post's card (the taps, pressed for
real, a phone and a desk; a name of two letters over a long @handle);
`verify_socialreposts` 16 a comment's card.
