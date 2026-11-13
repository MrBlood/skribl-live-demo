# A note for the lawyer

Blooby, the social site built on Skribl's drawing tools (at `/social`, and
on blooby.app), has three rules
pages, written in plain words and marked as drafts: Terms, Privacy and
Community rules (`social/templates/social/rules.html`). The site is invite-only
for now. Before it opens to everyone, a lawyer reads them. This note says what
the site actually does today and lists the questions only a lawyer can answer.
Nothing here is legal advice; it was written by the people building the site.

## What the site does today

- **Who can join.** People who tick "I'm 13 or older", by invite. The time
  they ticked it is kept. Join says "Joining means you agree to the Terms and
  the Community rules. Privacy says what we keep.", and which version of the
  Terms they joined under, and when, is kept with them (from Nov 12; nobody
  who joined before was asked). Looking around (Explore, a profile, a post)
  needs no account.
- **What is kept about a person.** Name, handle, a short bio, a drawn face,
  their posts, comments and drawings and where each is shown, who invited
  them, and for each passkey its public half and when it was last used.
  There are no passwords. Their likes (from Nov 13): which post or drawing
  they liked, when, and where its drawing was in its replay when they
  tapped the heart, if it was playing.
- **Likes.** Everyone sees how many people liked a post or a drawing; who
  liked it, when, and that moment in the replay are shown only to its maker.
  A like by somebody blocked either way, or taken down, is neither shown nor
  counted. Deleting a post or a drawing deletes its likes.
- **Cookies.** Two, both the site's own: one keeps a person signed in, one
  protects forms. Nothing is loaded from anyone else (no ads, no analytics, no
  outside fonts or scripts).
- **Flood limits.** Tries at joining, reporting, posting and the like are
  counted by a keyed hash of the person or the address they come from, never
  the address itself. The site's own counts are cleared out after about two
  days.
- **Reports.** Anybody who can see something can report it, signed in or not.
  A report is a row for a person to look at; nothing is taken down by a report
  alone. Who sent a report is seen only by the site's admins (signed out: a
  keyed hash of their address, so the same report is not counted twice).
  Reports for a child's safety come first on the admins' page, blurred until
  opened.
- **Taking something down.** An admin can take down a post, a comment, a
  drawing or a whole account. It is hidden from everybody but its maker, not
  deleted, and its maker is told: "Taken down: it broke the rules." The
  comments on a post or a drawing taken down are hidden with it.
- **Deleting an account.** The person's profile, posts and comments (their
  words and drawings) are deleted with it, including a post that was taken
  down, and the answers under their comments; so is every comment other
  people left on their posts and on their drawings (since Nov 12 a drawing
  shown outside a post has comments too). Their other drawings and drafts
  stay until they delete them in their Library; the confirm page says so
  first, and a drawing taken down outside a post stays hidden. Their likes
  are deleted, and so is every like on what they made. Their passkeys
  go, so nothing can sign in as them. Reports that named them stay, naming
  nobody. Blocks they made or were part of go.

## Questions for the lawyer

1. **Age.** Is a ticked "I'm 13 or older" enough (COPPA)? What should happen
   when someone is reported as under 13?
2. **A child's safety.** As we understand it, a US service that learns of
   apparent child sexual abuse material has to report it to NCMEC's
   CyberTipline (18 U.S.C. § 2258A) and keep the material for a set time after
   reporting. Please confirm. Who files the report, and how? Today a taken-down
   thing is kept hidden, but deleting the account deletes it: should a
   taken-down thing be kept even then, and for how long?
3. **Copyright.** Do we want the DMCA safe harbor (a designated agent
   registered with the Copyright Office, and a takedown and counter-notice
   process)? The report sheet already offers "copyright" as a reason.
4. **Privacy law.** Which laws apply as the site grows (for example California's,
   or the GDPR if people in Europe join)? What should we say about how long
   reports, report senders' hashes and taken-down things are kept?
5. **The terms themselves.** Joining now says so, in a line just above Join's
   links to the rules, and keeps the version and the time; is a line enough,
   or should it be a box to tick? Do we need governing law, liability, or how
   changes are announced?
6. **Rules not decided yet.** Are drawings with nudity or violence allowed?
   Today the rules do not say.
7. **Contact.** The pages give no address to write to yet. What should it be?
8. **The name.** The owner named the site Blooby (Nov 12), and its pages
   say so; the drawing tools inside it keep the name Skribl. A trademark
   search for "blooby" is still worth doing, and a view on "Skribl" beside
   skribbl.io and skribl.com.

## A friend's read (Nov 12), and where each point stands

A friend of the owner read this note and answered it point by point. The
owner's view: none of it has to be built today, but it belongs on file, for
the lawyer and for the work before the site opens to everyone. Each point,
what the site does now, and what is planned:

1. **Ask for a birthday to check age.** Not doing it. The owner finds a
   birthday invasive, and would not join a site that asked for one. Joining
   keeps "I'm 13 or older" and when it was ticked. For the lawyer: is that
   enough (question 1)?
2. **Keep evidence when an account is deleted** (a preservation hold: kept
   out of everybody's sight, opened only by admins with every look logged,
   with its reason, legal basis and a review date; not every report kept for
   a year). Agreed, and first on the list before the site opens to everyone.
   Today a post that was taken down is deleted with its maker's account.
   For the lawyer: when a hold is required, and for how long.
3. **More report reasons**, the urgent ones first. A person can already be
   reported as under 13, and a child's safety comes first on the admins'
   page. Not yet: an intimate image shared without consent (with point 8),
   and a credible threat apart from "Abusive or hateful".
4. **Agree to the Terms at Join**, keeping which version and when. Built
   (Nov 12; the owner chose a line over a second box to tick): Join says
   "Joining means you agree to the Terms and the Community rules. Privacy
   says what we keep.", and keeps the version (the day those words last
   changed) and when. For the lawyer: the final wording, which later changes
   need agreeing to again, and what to do for those who joined before.
5. **Admin controls.** Already: an account can be taken down (hidden from
   everybody, its maker still signs in and sees their own, and nothing new
   can be shared from it), and each report keeps how it was answered, by
   whom and when. Not yet: undoing a take-down, a private note on why, and
   "escalated" as a state.
6. **A take-down hides everywhere.** `harness/verify_socialsafety.py` checks
   that a taken-down post or account is gone, for everybody else, from Home,
   profiles, a post's page, a drawing's own link and Skribl's public list
   (what Explore shows), and that a taken-down account cannot post. To add to that check:
   the picture and data links of a taken-down drawing. The site has no
   search yet.
7. **A contact page and address, and an alert on a serious report.** Planned
   before the site opens to everyone. The address needs a mailbox the owner
   sets up on the domain, and waits for the lawyer (question 7). The alert
   starts inside the site.
8. **Removing intimate images on request** (the TAKE IT DOWN Act: a request
   process, removal within 48 hours, and known copies). Planned before the
   site opens to everyone. For the lawyer: whether an invite-only site is
   covered today, and what a valid request must hold.
9. **Check that deleting really deletes.** Passkeys go with the account; a
   freed handle can be taken again, but nothing old points at the new person
   (reports name nobody, and addresses are random). Gaps: a person's other
   drawings stay until they delete them (said before they confirm), and the
   host's database backups keep deleted rows for as long as its plan keeps
   backups, which Privacy should say once that is checked.
10. **A playbook for admins**: what to do for a child's safety, a threat,
    copyright, an underage account or an intimate image, and how not to
    destroy what must be kept (18 U.S.C. § 2258A asks for a year's
    preservation after a report to NCMEC). Worth writing with the lawyer; a
    first draft before the site opens to everyone.
