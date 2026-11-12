# The Skribl social site: how it is laid out

**Status: agreed, Nov 10. The owner said "all yes" to every default in
section 8.** Nothing here is built yet except where it says "have", and phase
1's first piece, the frame, which section 9 describes.

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
  built Nov 12 (section 10).*
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
| `/social/explore` | **Explore:** Skribl's own Gallery section, New and Hot, search, Report, Load more. |
| Make | Not a page: a small sheet with two doors, **Draw** (Skribl's Pad) and **Flip** (Skribl's Flip), from the bar on a phone, the rail on a desk and Home's button. |

A phone has a bar along the bottom (Home, Explore, Make; You comes with
sign-in), a desk a rail down the left (the wordmark in the accent purple,
Home, Explore, Make), and the page you are on has a pen's line under its
name. Light and dark follow the device: the site has no switch of its own
yet, and Skribl's own choice is kept where only Skribl's pages read it.

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
| `/social/@<handle>` | **A profile**, any case of the handle: their face, big, in a circle, drawing itself once (Skribl's face player, at 4x or quicker so it takes about four seconds; finished and still under Reduce Motion); their name, @handle and a few lines about them (plain text, 160 characters, 4 lines, nothing invisible or turned around, no links); Share; and their public skribls as Skribl's own Gallery section, newest first, New and Hot and search within them, paging by cursor. Your own adds **Edit profile**, **Draw your face** (**Redraw my face** once you have one) and the gear to Settings. Nobody by that name, never made or deleted, is one kind 404. |
| `/social/you/edit` | **Edit profile**: your name and a few lines about you, a form that works without a script, the server's limits said kindly under each field. |
| `/social/you/face` | **Draw your face**: the real Pad over your profile, in its face mode (`?compose=1&face=1`, through `lib/composehost.js`: square, a face's words, no Flip), and "Use this face" sends the drawing here (JSON, the site's token). The site posts it through Skribl's `create_post`, UNLISTED, in the same transaction as your row that names it; a redraw deletes the old one through `delete_post`. |
| `/social/you` | **Settings** now (the gear's): the account page of piece 2, its name the only change. |

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
`author`).

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

    /social/              Home, signed in: "Say something, then draw it…",
                          then everyone's posts, newest first (Following comes
                          with phase 2). Signed out, the first visit, as before.
    /social/posts         a post: the words and the drawing (JSON)
    /social/feed          the next page of the feed, for Load more (JSON)
    /social/p/<id>        a post's own page: its drawing plays by itself
    /social/p/<id>/delete your own post, gone: its words and its drawing (JSON)
    /social/b/<skribl_id> a drawing shown outside a post, on a page of its own
    /social/b/<skribl_id>/delete  your own such drawing, gone (JSON)

**A post is a drawing and words** (the words optional, up to 500
characters). Draw and Flip open Skribl's editor over Home in compose mode,
with "Show in the Skribls gallery" in its sheet (`?gallery=1`); its Add hands
the drawing back, and the composer shows it in the in-post player, the same
player the post will have, with Edit drawing and Remove. Post sends both: the
skribl through `create_post` and the site's row (`social_posts`, on the
site's own chain) in one transaction. The skribl is public with the gallery
tick and unlisted without (reachable by its link, listed nowhere but the
site's feed); its title is the post's first words, its caption only what was
written under the tick. A press on Post with nothing drawn says so.

**The feed** reads its drawings' sizes, lines and plays through Skribl's new
`describe_posts` (docs/INTEGRATION.md, "Reading them on your server"), one
query a page, for the person looking; each card is still until tapped. Load
more brings the next page in place, paged by a cursor that names no internal
id.

**Home holds every drawing the site's people show** (the owner, Nov 12, of
Home saying "No posts yet" while Explore was full: "all yes" to A). A
drawing posted from the Pad on its own page (Make's Draw) and shown in the
gallery is on Home too, among the posts, newest first: a card whose words
are its title, with a page of its own (`/social/b/<id>`: its drawing plays
by itself, More from its author's posts and drawings, its ⋯ and its Delete,
its author's alone). It comes through Skribl's `list_public_posts`
(docs/INTEGRATION.md, "A feed of your own people's drawings"), one cursor
walking both; a post's drawing shows once, as the post, and its page is the
post's. Not one kept unlisted, nor one by somebody not on the site.
`harness/verify_socialposts.py` section 9 holds it.

**A post's own page** plays its drawing by itself, at the author's speed,
sound off until the viewer turns it on, and never under Reduce Motion (the
player's own `play()`: docs/INTEGRATION.md, "A post's own page can start
it"). Its author, its words, when (in the person's own time), its plays,
Share and Make your own; Comments' place kept ("Comments open soon"; since
phase 2 the comments themselves, section 10); on a desk, the drawing on the
left and More from its author beside it, each tile the drawing alone, cut out
of its share card as Skribl's face macro does.

**The ⋯ sheet**, as the mock drew it: Copy link, Share…, and Report this
post (and since piece 5, signed in, Block @them), or on your own Delete
post. Report rises as a sheet of its own (since piece 5 into the site's own
queue, below). Delete asks once and takes the words and the drawing.
Deleting an account takes its posts the same way.

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
post's page, a drawing's page, More from. To the one blocked, the blocker's
profile is "Nobody here by that name"; the blocker finds theirs saying so,
with Unblock, and nothing they made. Nobody is told. Settings lists the
people you blocked, newest first, each with Unblock, and only the blocker
lifts a block. Deleting an account takes its blocks; a report naming it
stays, naming nobody.

**A block reaches Skribl's pages** through the two seams Skribl gives every
host for a block list (docs/INTEGRATION.md): a feed filter (Explore's
gallery, a profile's skribls, Home's drawings) and a visibility policy (a
drawing's link page, payload and card; the card falls back to its blank
canvas). A host that mounts the site installs both, asking
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

    /social/p/<id>/comments   POST: a comment on a post, or an answer to one
                              (JSON); GET: the next page of its comments, for
                              Load more
    /social/c/<id>/delete     your own comment, gone with its answers; or, on
                              your own post, anybody's, removed from it (JSON)

**On a post's own page** "Comments" and how many stand where "Comments open
soon" was. The box on top is Home's composer in the mock's size: your face,
"Say something, or draw it…", Draw and Flip, and Post. The comments come
newest first, each with its face, name, a short time ("40m", "2h"), its words
or its drawing, Answer and ⋯; twenty a page, then Load more. **Answers sit one
level under a comment, oldest first**: answering an answer puts the new one
under the same comment. Answer brings the box there ("Answer Theo…"): the
comment keeps its place on the screen as the box moves, the box fades in, and
if it landed below what the screen shows the page glides down to it. Answer
again, Esc or Post sends the box home. On a desk the comments sit beside the
drawing, under Share. Home's card says how many beside the plays ("3
comments", a way to them), and nothing at none. A drawing shown outside a post
(`/social/b/<id>`) has no comments: they are a post's.

**Who may comment:** somebody signed in, not taken down, with no block
either way with the post's author; an answer also with none with the author
of the comment it answers. The route refuses anybody else kindly, and the
box is not shown to them. Signed out, the comments are readable and "Sign in
to answer" stands in the box's place, back to the post once signed in. The
words are a post's: tidied, 500 characters at most, nothing hidden or turned
around; 60 comments an hour a person (`comment` in security.LIMITS). A
comment needs words or a drawing.

**A drawing answer** (the second part; the mock's 6. "Reply with a skribl",
phase 3's, came early with the owner's yes to this mock.) Draw and Flip in
the box open Skribl's editor over the post in compose mode (`?compose=1`, no
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
somebody who may comment.

**What is shown, and counted:** nothing by anybody hidden from the viewer (a
block either way, or taken down), nor the answers under it, on the post's
page and on Home's card alike. A comment's ⋯: your own is "Your comment",
Delete comment; somebody else's on your own post "Theo’s comment", Remove
from my post and Report comment; anybody else's Report comment. Delete and
Remove go at once (the ⋯ is the asking), the comment fading out with its
answers. Report sends a post's reasons into the site's own queue (kind
`comment`); Your Reports shows its card (whose, its words, a link to it on
its post's page), and Take it down hides it from everybody but its author,
who sees "Taken down: it broke the rules. Only you can see it."

**Data.** `social_comments`, on the site's own chain (migration
`e4b8c2a91f37`): `public_id`, `post_id`, `person_id`, `parent_id` (always a
top-level comment's), `words`, `skribl_id`, `created_at`, `taken_down_at`;
indexed by address, a post's newest first, a comment's answers oldest first,
a person's, and a drawing's. Deleting a comment takes its answers, a post its
comments, an account its comments and every answer under them: said in code
(`comments.drop_comments`, `posts.drop_post`, `accounts.delete_person`),
never left to the schema's ON DELETE CASCADE, which SQLite enforces only
where Skribl's pragma hook is on.

**Counted, not kept (for now).** Section 3's rule 3 keeps counts as stored
numbers. A comment count that hides what a block hides is each viewer's own,
so it is counted, one grouped query a page on the post's own index, by the
page's own rules; a kept count waits for a measurement that asks for it.

`harness/verify_socialcomments.py` holds it through the demo's own server;
DECISIONS.md ("Comments at /social") says what each check was shown red by.
