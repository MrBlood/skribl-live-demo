# Working agreements for this repository

## Spending: ask before incurring costs (owner's standing rule)

Never take an action that could create or increase a bill on any of the
owner's accounts — GitHub, Render, or any other service — without asking
first and getting an explicit yes. This includes, concretely:

- Enabling, re-enabling, or widening CI triggers, paid runners, larger
  runner sizes, or anything that consumes metered Actions minutes beyond
  the current workflow configuration.
- Creating or upgrading services, plans, databases, storage, bandwidth
  tiers, or autoscaling on Render (or any host).
- Signing the project up for any third-party service that has a paid tier,
  even when starting on the free tier.
- Anything whose cost scales with usage in a way the owner cannot see
  coming (per-request billing, storage growth, egress).

When in doubt about whether something bills, treat it as if it does: stop
and ask, with a plain-language estimate of the cost. Context: the full CI
battery once burned the entire monthly Actions allowance in a single day
(30 full runs — see the note atop `.github/workflows/harness.yml`).

## CI economics

Pull requests run only the smoke job; the full three-job harness runs on
pushes to main and manual dispatch. Do not widen these triggers without
the owner's explicit approval (see the spending rule above). The full
suites run locally before every push — that is what makes the PR-side
trim safe.
