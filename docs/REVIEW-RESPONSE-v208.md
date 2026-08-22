# v208 — response to the v207 developer review (F1 + F4 closed)

The v207 developer review (received after the v207 seal) split its verdict:
**"UI/device release: strong candidate. Integration contract fully closed: not
yet."** That split is accepted as stated. This build closes the two findings
that were mechanically closable without an owner decision or real hardware.

## F1 — P1 — SQLite AUTOCOMMIT guard was dead code  → CLOSED

The reviewer was exactly right, and it was worse than "checks the wrong
field": the guard **never fired** against the configuration it existed to
refuse. Verified live on SQLAlchemy 2.0.51:

    create_engine("sqlite:///:memory:", isolation_level="AUTOCOMMIT")
      dialect.isolation_level             -> None      (what the guard checked)
      dialect._on_connect_isolation_level -> 'AUTOCOMMIT'  (where SA 2.x keeps it)

Fix (`skribl/models.py`, `_install_sqlite_fk`): check
`_on_connect_isolation_level` first, fall back to `isolation_level` for older
SQLAlchemy. Regression (`verify_txcontract.py`) builds a REAL AUTOCOMMIT
engine — no faked attribute, per the reviewer's explicit instruction — and
asserts the documented RuntimeError, then asserts a default engine is still
accepted. The prior "AUTOCOMMIT" regression had built a host with its own
explicit-BEGIN listener, a different shape that never exercised this path.

## F4 — P2 — Record with Tune open stranded an open drawer  → CLOSED

Reproduced: open Tune, press Record → recording CSS hides `#tuneBtn` but
`#tuneShell` kept `.open`, `aria-hidden="false"`, `aria-expanded="true"` — an
expanded drawer with no visible opener. Fix: `editor_tune.js` exposes
`window._skriblClosePadTune`; `beginRecording()` calls it first (optional
chaining, one call). Pinned exactly as the reviewer specified: no `.open`,
`aria-hidden="true"`, `aria-expanded="false"`, and stopping does not reopen.

⚑ **Owner: player-JS ratchet 142,344 → 142,370 (+23 B)** for the F4 hook call
in app.js (the hook body lives in editor-only editor_tune.js). Same
small-functional category as the three prior approved raises.

## Audit caveat  → ACCEPTED, claim narrowed

The v207 phone-fit audit is a strong **right-edge + same-row horizontal** fit
check, not a proof that "every interactive rectangle is on-screen". It does not
test left<0, vertical overflow, overflow-hidden ancestor clipping, off-row
collisions, or pseudo-element hit-area overlap. Wording corrected in
REVIEW-RESPONSE-v207 and here; widening the checker is a follow-up.

## Deliberately NOT closed here (see HANDOFF-NEXT-SESSION.md)

- **F2** — failed SQLite DB-backed POST may hold quota until pending-TTL.
  Real, but a CONTRACT decision (make immediate retry mechanically true, or
  document the weaker guarantee). Recommend the former. Owner's call.
- **F3** — Pad replay's Web Audio unlock is fire-and-forget (iOS race). Real;
  the v203 player fix (A1) is the template. Needs the reviewer's specified
  regression + a real iPhone. Not rushed at end-of-session.

## Gates

txcontract 34 (+3 real-engine), ux 264 (+5 F4), visual 76, parity 115,
cssplit 17, docs 34, player-isolation 20 (ratchet 142,370 flagged).
