# The Skribl social site: how it is laid out

**Status: agreed, Nov 10. The owner said "all yes" to every default in
section 8.** Nothing here is built yet except where it says "have".

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
