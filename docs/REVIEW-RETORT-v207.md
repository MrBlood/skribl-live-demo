# Retort to the Skribl v207 developer review

**To:** the reviewer. **Re:** `DEVELOPER-REVIEW-v207.md` + `RELEASE-GATE-v207.md`.
**From:** the build. **Build under discussion:** v207 (`ac316597…`); replies
land in **v208** (this tree).

---

## Your verdict, accepted verbatim

> *UI/device release: strong candidate. Integration contract fully closed: not yet.*

Agreed on both halves, and thank you for stating them separately — that split
is the correct frame and it is how the next session is organised. Your
independent confirmation of the seal evidence (177/177, v207 stamp, compileall,
`node --check`, 2,310/60/1, PG 14/14) is noted. So is your confirmation that
all nine headline v207 UI items are present in implementation, not just notes.

Below: each finding, what was checked, what was done, and where I disagree
(rarely) or where the honest answer is "not yet, and here is why".

---

## F1 — P1 — SQLite AUTOCOMMIT guard checks the wrong SQLAlchemy state

**Verdict on your finding: correct, and understated.** I verified it live
rather than take it on faith:

```
sqlalchemy 2.0.51
create_engine("sqlite:///:memory:", isolation_level="AUTOCOMMIT")
  dialect.isolation_level             = None          ← what the guard read
  dialect._on_connect_isolation_level = 'AUTOCOMMIT'  ← where SA 2.x keeps it
  conn.get_isolation_level()          = SERIALIZABLE  ← would also mislead
```

So it was not "unreliable" — the guard **never fired** against the exact
configuration it was written to refuse. Dead code behind a confident comment.
That is on me: the v202/v203 fix was verified with a host that had its own
explicit-BEGIN listener, which is a different shape and never touched this
branch. Your instruction — *do not fake it by assigning
`engine.dialect.isolation_level`* — was followed to the letter.

**Done (v208):** `skribl/models.py::_install_sqlite_fk` now checks
`_on_connect_isolation_level` first and falls back to `isolation_level` for
older SQLAlchemy. `verify_txcontract.py` builds a **real** AUTOCOMMIT engine,
asserts the documented `RuntimeError`, and asserts a default engine is still
accepted (34/34). **CLOSED.**

---

## F2 — P1 — failed SQLite DB-backed POST can consume quota until pending TTL

**Verdict on your finding: correct, and I accept the test you specified as the
decisive one.** The existing regression's post cap is indeed large enough that
one stuck pending slot cannot be observed. `SKRIBL_RATE_MAX_POSTS=1` → reserve
→ force host-commit failure → force the bounded cleanup failure → immediate
retry is the right shape, and if the retry is limited the slot was not
released. I have not run it and will not claim it passes.

**Why it is not closed here — and this is a genuine disagreement about
category, not about the finding:** you frame the choice as *"make immediate
retry mechanically true, or document the weaker contract."* I agree those are
the two honest options — which is exactly why it is **not mine to pick**. It
is a product-contract decision (does a failed post cost you quota for a
while, or never?), and this project's standing rule is that contract choices
go to the owner, flagged, not decided in a fix pass. It is recorded as the
first item for the next session with my recommendation: **option (a)** — a
user whose post failed should not also be told to slow down. When the owner
decides, the implementation and your regression follow together. **OPEN, by
design, with a recommendation.**

---

## F3 — P1 — Pad replay still has the fire-and-forget audio unlock

**Verdict on your finding: correct.** `startWebAudioLoop()` calls
`audioCtx.resume()` without observing the Promise, and the ordinary Play path
starts music from inside `clearAndRestore()`, which on the async `Image.onload`
branch executes after the click gesture has returned. That is the same
unlock-timing class the v203 player fix (A1) closed — the player got the fix,
the editor replay did not. Fair, and consistent with your original A1 report.

**Why it is not closed here:** it was the last item at end-of-session and it
is exactly the kind of fix that should not be rushed — A1 took a full pass
with a ratchet raise, and this one needs the same care plus the regression
you specified (force `clearAndRestore()` onto the `Image.onload` branch,
instrument `resume()`, assert it starts synchronously from the click before
onload). The A1 code is the template. It is the **first engineering task** of
the next session and the last iPhone item; a real iPhone remains the hardware
check, as you say. **OPEN, scheduled.**

---

## F4 — P2 — Record with Tune open strands an open drawer

**Verdict: correct.** Reproduced exactly as your sequence describes: after
Record, `#tuneShell` kept `.open`, `aria-hidden="false"`,
`aria-expanded="true"`. On phone the button is hidden by the recording CSS,
so the user is left with an expanded panel and no visible opener — which does
undermine the reason Tune is hidden during recording.

**Done (v208):** `editor_tune.js` exposes `window._skriblClosePadTune`;
`beginRecording()` calls it first (`?.()`, one call). Pinned to your spec:
shell has no `.open`; `aria-hidden="true"`; button `aria-expanded="false"`;
stopping does not reopen. **CLOSED.** ⚑ +23 B in the player bundle (the hook
body is editor-only; only the call site is in app.js) — flagged for the owner
like the three prior small raises.

---

## The phone-audit caveat

**Verdict: correct, and I am glad you named it.** "Nothing off-screen" was
stronger than the checker proves. It is a strong **right-edge + horizontal
document-scroll + same-row overlap** audit — it does not test `left < 0`,
vertical viewport overflow, overflow-hidden ancestor clipping, controls whose
different top/height defeats the `sameRow` heuristic, or pseudo-element
tap-area collisions. The claim is narrowed in `REVIEW-RESPONSE-v207.md`,
`REVIEW-RESPONSE-v208.md`, and `HANDOFF-NEXT-SESSION.md`. Widening the checker
is queued as optional work; as you say, this is a scope correction, not
evidence of a current layout bug.

---

## One thing I would push back on — gently

Nothing in the findings. But the release-gate wording "make Skribl actually
refuse it" for F1 slightly implies the refusal was never attempted; it was
attempted and *tested against the wrong shape*, which is a worse failure mode
than an omission because it produced false confidence. I say this not to
excuse it but because it is the lesson worth keeping: **a passing regression
that exercises the wrong equivalence class is more dangerous than no
regression.** Your review found that class of gap in three places (F1's fake
condition, F2's over-generous cap, F3's editor-vs-player split). That is the
most valuable thing in it.

---

## Net

| Finding | Status in v208 |
|---|---|
| F1 AUTOCOMMIT guard | **CLOSED** — real-engine regression |
| F2 quota after failed POST | **OPEN — owner contract decision**, recommendation (a) |
| F3 Pad audio unlock | **OPEN — first task next session**, A1 is the template |
| F4 Tune stranded on Record | **CLOSED** — pinned to spec, ⚑ +23 B flagged |
| Phone-audit claim | **NARROWED** — widening queued |

Thank you for a review that cited source lines and specified the tests. Both
open items are open because they need something a fix pass cannot supply
(a product decision; a physical iPhone), not because they were deferred for
convenience.
