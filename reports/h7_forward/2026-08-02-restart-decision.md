# H7 restart decision — 2026-08-02

## Decision

**DO NOT RESTART H7 NOW.** If H7 is resumed later, it must use a new clean
namespace and a new registration. No new observation may be appended to
`h7-forward-15-v1`.

Status: **PREPARED / NOT REGISTERED / NOT ACTIVATED**.

## Computer-verified facts

- `uv run python -m options_researcher.h7_event_ledger verify` returned
  `VALID records=1 head=a1ea228c2abb` on 2026-08-02 UTC.
- The old store still contains only its July 20 `window_registration`. It was
  not edited, appended, copied, or used as the base for a new period.
- ThetaData acquisition is disabled. The approved v2 history ends on
  2026-07-31, so there is no approved chain source for a new forward session.
- The repository feasibility note estimates only about 3–5 full-stack H7
  candidates over 70 sessions against a 10-loss verdict bar. A new
  loss-gated window therefore owes a fresh measured base-rate calculation and
  either the required 2x margin or an owner-typed starvation-risk acceptance.
- A new real registration also requires fresh source-health, exact-session
  data-gate, backup/restore, clean-code, independent-review, and owner
  activation evidence. Those inputs do not currently exist for a new
  namespace, and the required activation confirmation was not supplied.

## Prepared restart contract

When an approved forward data source exists, prepare a namespace distinct from
`h7-forward-15-v1` and bind all of the following before its first event:

1. provider and cache namespace;
2. exact last historical session and manifest/audit receipt;
3. immutable scope and source-health receipt;
4. measured registration-feasibility result;
5. start session, session count, and derived end session;
6. frozen strategy, cost, scoring, and source identities;
7. fresh backup/restore and independent review evidence;
8. explicit owner authorization through the guarded registration door.

Until all eight exist, H7 remains paused. This is a governance decision, not a
strategy verdict and not evidence for or against an advantage.
