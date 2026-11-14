# The Skribl social site: how it is laid out

**Status: agreed, Nov 10. The owner said "all yes" to every default in
section 8.** Nothing here is built yet except where it says "have", and phase
1's first piece, the frame, which section 9 describes.

**The map since Nov 14 is section 16**: a post is the one thing people
share. Where an earlier section says otherwise (Home holding every drawing,
a profile's Skribls being Skribl's Gallery, no follower counts), section 16
is the decision.

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
sign-in), a desk a rail down the left (the wordmark in the accent purple,
Home, Explore, Make), and the page you are on has a pen's line under its
name. Light and dark followed the device here; since Settings (section 14)
the site wears Skribl's own one choice, for Blooby, Pad and Flip alike.

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
| `/social/@<handle>` | **A profile**, any case of the handle: their face, big, in a circle, drawing itself once (Skribl's face player, at 4x or quicker so it takes about four seconds; finished and still under Reduce Motion); their name, @handle and a few lines about them (plain text, 160 characters, 4 lines, nothing invisible or turned around, no links); Share; and their public skribls as Skribl's own Gallery section, newest first, New and Hot and search within them, paging by cursor. Your own adds **Edit profile**, **Draw your face** (**Redraw my face** once you have one) and **Settings**, the word with the gear (section 14). Nobody by that name, never made or deleted, is one kind 404. |
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
    /social/b/<skribl_id> a drawing shown outside a post, on a page of its own;
                          where every gallery card on the site opens
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
its author's alone, and since phase 2 its comments, section 10). It comes
through Skribl's `list_public_posts`
(docs/INTEGRATION.md, "A feed of your own people's drawings"), one cursor
walking both; a post's drawing shows once, as the post, and its page is the
post's. Not one kept unlisted, nor one by somebody not on the site.
`harness/verify_socialposts.py` section 9 holds it.

**Every card opens its post** (the owner, Nov 13, from the phone: "Show me
where you click or touch to go to post view? It's not clear. I thought on
card?"; the rule said yes to on Nov 12, "anywhere on the card should open the
post and clicking on the player should make it play"). On Home's cards the
line under the drawing ("Drawn in 16 sec · watching at") and the space around
the drawing open the post too, as the rest of the card did (`posts.js`); the
speed and its choices, the heart, the scrubber and the loop keep their own
taps. Explore's cards, a profile's Skribls and the first visit's newest are
Skribl's own Gallery cards, and they open where the site says, through
Skribl's seam for it (`skribl.set_card_url`, docs/INTEGRATION.md "Where a
Gallery card opens"; the demo's `app.py` sets it for the site's own pages):
`/social/b/<id>`, from anywhere on the card that is the card's own, by Home's
rules, with the title a link to it and the ⋯'s Open going there. One address
serves every card: `/social/b/<id>` takes a post's drawing on to its post for
anybody who may see it (and is as gone as the post to anybody else, naming
nothing), and sends a drawing by somebody not on the site, which has no page
here, to Skribl's own page for it. Skribl's own `/gallery` is as it was.
`harness/verify_socialposts.py` section 12 holds it: Cal's tap map as rows.

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

    /social/p/<id>/comments           POST: a comment on a post, or an answer
                                      to one (JSON); GET: the next page of its
                                      comments, for Load more
    /social/b/<skribl_id>/comments    the same, on a drawing shown outside a
                                      post (below)
    /social/c/<id>/delete             your own comment, gone with its answers;
                                      or, on your own post or drawing,
                                      anybody's, removed from it (JSON)

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
too. The comments come newest first, each with its face, name, a short time
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
does), reports, Load more, Home's count. They follow its page, which decides
who may see it (public, its maker one of the site's people, no block either
way, nothing taken down but to its maker: `posts.bloob`, one rule for the page
and its comments). A block either way with its maker, the drawing taken down
(withheld) or its maker taken down, and the drawing deleted in the Library:
its page is gone to them, and so are its comments, read, said, answered or
reported. Its maker still sees them on a drawing taken down, with the note,
and no box. Deleted through the site (its ⋯, Delete), it takes its comments
with it, in code, and their drawing answers.

**Easier to open a post** (the same yes: "tap its words, its name line or its
time; the 💬 shows even at zero"). On Home's cards the words and the time are
each a link to the card's own page (a post's or a drawing's); the face, the
name and the @handle still go to the person's page, as everywhere else on the
site (the owner was told: "its name line" kept going to the profile). The 💬
shows even at none: its icon alone, named "Comment", a 44px way to the
comments. Nothing on the card moved: the name's link lies under the @handle
too, so the person's link is the whole name line's 44px as before, and the
time's link, over it, is 44px by reaching down into the room under its line
(toward the words, which go where it goes; on a card with no words the
drawing lies over its last 11px or so and keeps its taps there, so the
time's own tap is 33px tall, the card's ground around it opening the post
too). More from's tiles were whole links already; a profile shows Skribl's
Gallery, not these cards.

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
on. The route refuses anybody else kindly, and neither the box nor its icon
is shown to them. Signed out, the comments are readable and the icon raises
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
comments newest first. Deleting a comment takes its answers, a post or a
drawing its comments, an account its comments, every answer under them and
every comment on what it owned: said in code (`comments.drop_comments`,
`posts.drop_post`, `posts.bloob_delete`, `accounts.delete_person`), never
left to the schema's ON DELETE CASCADE, which SQLite enforces only where
Skribl's pragma hook is on. A drawing deleted in the Library (Skribl's own
page, outside the site) takes its page, and so its comments, from everybody
at once; their rows stay until its maker's account goes, or each commenter's,
since Skribl tells a host nothing when a drawing is deleted on its own pages.
The chain taken back down deletes the comments on drawings (there is no post
for them to be on).

**Counted, not kept (for now).** Section 3's rule 3 keeps counts as stored
numbers. A comment count that hides what a block hides is each viewer's own,
so it is counted, one grouped query a page for each kind (posts', drawings'),
each on its own index, by the page's own rules; a kept count waits for a
measurement that asks for it.

`harness/verify_socialcomments.py` holds it through the demo's own server
(sections 20 to 28 the drawings'), and `harness/verify_socialposts.py`
sections 10 and 11 the card's ways in; DECISIONS.md ("Comments at /social", and
"Comments on every drawing") says what each check was shown red by.

## 11. Built: notifications

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
on your post", or with a drawing, "Juno drew something on your post"). Their
face, who and what, when as comments say it ("5m", "2h"), their words under it
in quotes (two lines at most), and the small picture: the drawing they
answered with or drew, else the post's (or the drawing's), cut from its poster
as More from's tiles are. Each row is one link to that comment on its page
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
same grouped read as the count (one a kind for Home's whole page), counted by
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
and 3 others" (all the names up to three, "you" first when one is yours),
newest first. It opens the sheet of who, Make's own sheet in its paper with
the people on one card: each one's face, name, @handle and when, and under
when the moment their heart landed ("0:06") where one was kept, newest first,
each a way to their page, and "Only you can see who liked it." Nobody else is
sent any of it. The maker's own like, given or taken back, brings the line
and the rows up to date at once, the line's room opening or closing.

**In Activity** a like is a row like a comment's, its face wearing a small
liked heart: "Mira liked your post", when, and the post's small picture.
Several since you last looked on one post are one row, the newest face in
front ("Mira and 4 others liked your post"); a like says no words, so under
Earlier likes stay one row a post as well. A like row opens the post at
"Liked by…" (`#liked`), which glows a moment in the note's tint and fades, as
a landed comment does. **Likes never light the bell's dot:** a like needs no
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
own: "Unfollow Theo?", "You'll still see Theo's drawings under Everyone.
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
the people on one card, each a way to their page (where you unfollow), and
"Only you can see who follows you, and who you follow." Both lists sit in one
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
heart uses: "Follow Theo?", "Sign in, and Theo's new drawings show first on
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

**Following never runs out.** It is the people you follow and you, posts and
drawings alike (Skribl's listing, through its `authors`:
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
plans it as a MULTI-INDEX OR) and one of drawings, as Everyone's page reads
them, with no read a card.

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
- Home, Following and Everyone: their posts and drawings, left out in the
  query (Home's own posts, and its drawings through Skribl's listing and the
  host's feed filter), so every page stays whole;
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
it was, in its source too); their posts and their drawings' pages, More from
them, their skribls on their page, a drawing's link page and its payload. The
visibility policy is untouched: a mute never hides a page.

**Counts and "Liked by…" stay true,** for everybody and for you: a folded
comment is counted, their like is in the count and in "Liked by…", their
follow in "Followed by…".

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
`app.py` does), so a mute quiets Explore and Home's drawings and keeps their
page's skribls and More from. The visibility policy never hears of mutes.

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

The owner, Nov 14, after Explore's card turned out to be a different card
from Home's: "I'm starting to think we should do the social site like
skribls.net. It's a social site already that we were going to drop skribl
into as a feature, like GIF, add image, add video, poll... we can have the
gallery which is just the skribls (not post) and library drafts as part of
profile? We are kind of getting disorganized and random. We can clean this
up." Then, to the map below and its defaults: "Yes on everything."

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
| **Explore** | Everyone's posts: New, Hot and search. The site lists it itself; it no longer borrows Skribl's Gallery section. |
| **A profile** | Posts · Gallery · Likes · Drafts. **Gallery** is the person's drawings and Flips as drawings (Skribl's Library: a drawing on a stage above a grid), every one they have shared, each opening its post. **Likes** and **Drafts** are yours alone, on your own profile; Drafts are the drafts Skribl already keeps on your account (SkriblDraft). |
| **Make** | One composer, the same from the bar and from Home: words, and Draw or Flip. |
| **Activity, Settings** | As built. Settings from the ☰ on a phone (and the profile's button), the rail on a desk. |

**The owner's decisions (Nov 14, "Yes on everything").**

1. **Every share is a post** (words optional). Your Gallery collects every
   drawing you have shared, each opening its post. This replaces the Nov 11
   A, "Home holds every drawing, posts or not".
2. **Drawings already shared without a post stay in their author's Gallery**,
   so nothing is lost; Home and Explore show posts from then on.
3. **Photos, GIFs, video and polls: not now.** The composer keeps room for
   them in the same place a drawing goes. skribls.net has them already. A poll
   would be the easy first one. Photos and video bring storage that grows
   with use (a bill: asked first, WORKING-AGREEMENTS "Spending") and a
   child-safety duty to scan and report; a GIF needs an outside service. Each
   comes with its own plan and the owner's yes.
4. **The look, from the quick-patterns mock**
   (https://claude.ai/artifact/S7171kFpfXxiLUzPLJJYwY, its defaults):
   - **One calm card everywhere** (its B): at rest, who made it, the words,
     the drawing with its play button saying "drawn in 5 sec" (as Explore's
     does today), and one row. Press play and the drawing's line (scrubbing,
     speed, loop, the likes' dots) glides open under it and stays. A post's
     own page shows the line from the start. A desk keeps two columns where
     Explore has them today. Faces are the site's everywhere: the empty
     circle before somebody draws one, never an initial.
   - **One row under every card** (its B): 💬 count, ♡ count, Share, ⋯, and
     Open › at the end. The heart moves into the row from the drawing's line
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
     This replaces the Nov 13 B, "no counts, ever".

**What stays.** The three layers (section 1). Section 8's item 9: our own
build, not a copy of skribls.net; it is skribls.net's shape that is taken.
Skribl's own pages, its /gallery, and every seam a host uses, so Skribl can
still stand alone and still drop into skribls.net. Nothing changes in the Pad
or Flip. On Skribl's side one new option on the in-post player, a seam: a
post's line can wait until it is played (the site turns it on; Skribl's own
pages and other hosts stay as they are).

**What goes, as it is built.** Drawings outside a post in Home and Explore;
the likes and comments of a drawing outside a post (`/b/<id>/like`,
`/b/<id>/comments`), the few there are kept readable, nothing deleted; Home's
drawing card (`data-kind="s"`). Each goes in the PR that replaces it, with the
suites that held it.

**The order**, one PR at a time, each finished before the next starts:

1. This map (docs).
2. The one card and its row, on Home and a post's page.
3. Every share is a post; Explore lists posts with the one card.
4. A profile's tabs: Posts · Gallery · Likes · Drafts (mocked first).
5. The ☰ on a phone, and the counts.
6. Likes and comments on posts only; what goes, taken out.

**The four.** Simple: one thing to share, one card, one place for your
things. Kind: nothing anybody made is lost, Likes and Drafts stay yours
alone, nothing covers a button. Playful: the drawing still draws itself in
every card, and your Gallery is your drawings as drawings. Powerful: Skribl
drops into skribls.net exactly as it drops into our site.
