# Remediation ledger: the v321 outside audit (SK-AUD-001 to 012)

The audit asked for one line per finding: its status, the evidence, and what
was **not tested**. This is that ledger. It is written by hand and true as of
2026-10-10 (Mountain Time); the merged pull requests and the suites named are the
evidence, and a suite named here is one that was shown red on the old code
before it was trusted. Entries are not maintained after: DECISIONS.md carries
what changes next.

(The numbering is this audit's own. An earlier audit also used SK-AUD numbers,
for different findings; DECISIONS.md "After v321 -- the outside audit's
confirmed defects, fixed" is where this one starts.)

Statuses: **FIXED AND VERIFIED** (merged, with a suite that fails without it);
**PARTLY FIXED** (merged in part, the rest named); **NEEDS A DECISION** (the
owner's call).

| ID | Finding | Status | Evidence | Not tested here |
|---|---|---|---|---|
| SK-AUD-001 | Flip's WebM video had no music | FIXED AND VERIFIED (#382) | `lib/videorecord.js`, one recorder for both editors; `verify_videoexport`, and CI's mp4 lane in real Chrome | recording on Safari or an iPhone |
| SK-AUD-002 | Flip's video played its first page twice | FIXED AND VERIFIED (#382) | one frame per beat, counted by `verify_videoexport` | as above |
| SK-AUD-003 | An empty recording said it worked | FIXED AND VERIFIED (#382) | an empty or unreadable recording fails instead of downloading; `verify_videoexport` | as above |
| SK-AUD-004 | A draft open on two devices: the second save replaced the first | FIXED AND VERIFIED (#382) | reproduced against the API first; a stale save is refused and the editor keeps both copies (`verify_clouddrafts`) | two real devices |
| SK-AUD-005 | Without an account, deleting a post is tied to one browser or a saved key | PARTLY FIXED; the rest NEEDS A DECISION | the key is offered at the moment of posting (#397), the Library says so once (#392), and a saved key restores deletion in any browser (the recovery-key flow, `verify_posted`). Open: "portable custody" -- any way back for someone who never saved the key is a product choice, not a bug | VoiceOver reading the key row; a real browser-clear on a phone |
| SK-AUD-006 | Two tabs of one editor overwrote each other's autosave | FIXED AND VERIFIED (#402) | `lib/othertab.js`; `verify_drafts` TWO TABS on Pad and Flip | Safari's tab messaging on an iPhone |
| SK-AUD-007 | Empty Library showed search and filters with nothing to filter | FIXED AND VERIFIED (#387) | `verify_library` | -- |
| SK-AUD-008 | Empty Library: two Make buttons and a long explanation | FIXED AND VERIFIED (#392) | `verify_library`, `verify_posted` | -- |
| SK-AUD-009 | Guidance about keeping a post in the wrong place | FIXED AND VERIFIED (#392, #397) | `verify_posted`; `verify_ux` DELETE KEY on both editors | VoiceOver |
| SK-AUD-010 | Pad and Flip described a failed post differently | FIXED AND VERIFIED (#396) | `SkriblPostSheet.failure()` in `lib/postsheet.js`; `verify_flipmeta` fails each case on both editors | a real dropped connection on a phone |
| SK-AUD-011 | "Gone at once" on a host whose shared cache can keep media | FIXED AND VERIFIED (#394) | the delete wording says "up to 5 minutes" only where the host opts in; `verify_mediaauthz`, `verify_galib` | a real CDN |
| SK-AUD-012 | CI permissions and unpinned actions | FIXED AND VERIFIED (#382) | actions pinned to commits, read-only default token; `harness/tools/wheelhouse.py` for the offline set | -- |

## What this box cannot test, said once

- **Real assistive technology.** The suites check names, roles, focus order,
  Escape and focus return on every dialog (`verify_a11y`), but nobody has
  listened to Skribl with VoiceOver or NVDA. That needs a person with the
  device, or a paid accessibility test (ask before booking one: it bills).
- **iPhone and Safari.** There is no WebKit here. `docs/DEVICE-CHECKLIST.md` is
  the list for a real phone.
- **Segoe UI and SF.** Alignment is checked in the fonts installed here, and
  every fix is a font-independent rule so it holds in the owner's.
- **Performance on real devices.** Frame pacing is measured in headless
  Chromium (`verify_hold`); a mid-range phone is not.
