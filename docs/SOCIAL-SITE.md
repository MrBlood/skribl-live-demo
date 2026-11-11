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
- **Phase 2, the social core.** Follow, the Following feed, comments and
  replies, likes, in-app notifications, mute.
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
   shows the DNS records to add and makes the HTTPS certificate), and later
   the email service's few DNS records. What Cal sets up: the site answering
   at the top of the new domain while the demo keeps its own address, and
   the checks that both answer.
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

**Not yet:** the emailed link (an email service, asked first); profiles and
drawn faces (piece 3); a list of signed-in devices; a short undo before an
account is deleted (rule 9's undo window waits for the job queue); and an
account's skribls going with it, which needs a seam Skribl does not have yet
(docs/INTEGRATION.md documents deleting one post by its id, not an author's
all): until then the delete page says the skribls stay, and to delete them
in the Library first.

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
whether a skribl is still there through a documented seam); the profile's
empty Gallery says what any empty Gallery says.

`harness/verify_socialprofile.py` holds it all through the demo's own
server, faces drawn through the real Pad with a pen; DECISIONS.md ("Profiles
with drawn faces at /social") says what each check was shown red by.
