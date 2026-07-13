# H7 Stage 8 activation readiness packet — GATE NOT OPEN

**Prepared 2026-07-13. DRAFT ONLY; NOT PRE-REGISTERED; NOT AUTHORIZED.**

**BUILD-ONLY; SYNTHETIC-ONLY; INACTIVE. This packet does not register a
window, authorize a real event, add an operational entry point, or start a
clock. The default forward ledger remains `VALID EMPTY`. Stage 8 may begin
only after the owner supplies every blank input below and explicitly asks to
open it, followed by a new independent review.**

## 1. Dependency evidence now complete

Stages 1–7 are built. The dependency chain now includes exact-session source
and market-data gates, the verified forward ledger, owner-approved T+1 paper
lifecycle, global book risk, pre-registered scoring, and the independently
reviewed full synthetic proof.

Stage-7 receipt evidence:

- 12/12 synthetic source health and 12/12 synthetic exact-session data `GO`;
- 13 valid hash-chained synthetic events;
- decision session 2026-07-10, T+1 entry 2026-07-13, mechanical exit fill
  2026-07-15;
- one sleeve rejection and $506.30 July risk retained after close;
- one reconstructed trade: $384.70 after-cost P&L, +$8.00 underlying move,
  `INCONCLUSIVE` small-sample verdict;
- all registered refusal arcs passed; and
- real forward store `VALID EMPTY` before and after.

Those dates and results are fixtures only. They have no operational meaning.

## 2. Current live readiness snapshot — gates remain closed

Read-only refresh for evaluation session 2026-07-10 on 2026-07-13:

| gate | current result | activation consequence |
|---|---:|---|
| Source health | **4/12 healthy** | **BLOCKED**. CRWV, PLTR, SMCI, NVDA, AVGO, VST, CEG, and AMZN lack live future gating provenance. |
| Stage-2 data | **12/12 GO** | Ready for that completed session only; must be rerun immediately before registration/start. |
| Real forward ledger | **VALID EMPTY** | Correct pre-activation state. |
| Daily paid EOD chains | subscription ends 2026-07-29; continuity beyond that date is not owner-confirmed | **BLOCKED** before any chosen start. |
| Darwin ledger durability | `fsync` ordering implemented; `F_FULLFSYNC` not implemented or explicitly accepted | **BLOCKED** pending owner choice or a reviewed hardening change. |
| Code/config identity | the H7 config and Stage-2 corrections are committed; an unrelated parking-lot edit and untracked advisor-skill directories remain | **BLOCKED** until a future Stage-8 arc binds an intentionally clean activation snapshot. |

A prior data-audit receipt is now invalid because its recorded inputs differ
from the working tree. Do not refresh or bless that receipt as part of this
packet; resolve the unrelated edits first, then create a fresh audited receipt
inside the separately authorized Stage-8 arc.

## 3. Owner inputs — intentionally blank

The owner must type exact values; none may be inferred or defaulted:

```text
H7_STAGE8_EXPLICIT_AUTHORIZATION =
WINDOW_START_DECISION_SESSION =
WINDOW_DECISION_SESSION_COUNT =
WINDOW_END_RULE_ACKNOWLEDGED =
WINDOW_MINIMUM_THREE_CALENDAR_MONTHS_PER_LANE_ACKNOWLEDGED =
THETADATA_DAILY_EOD_COVERAGE_CONFIRMED_THROUGH =
THETADATA_CONFIRMATION_EVIDENCE =
DARWIN_DURABILITY_DECISION =            # IMPLEMENT_F_FULLFSYNC or ACCEPT_LIMITATION
```

The end rule must be stated as an integer number of XNYS **decision sessions**
starting inclusively at `WINDOW_START_DECISION_SESSION`. The derived final
decision session must fall on or after the three-calendar-month anniversary
of the start, with all three lanes active for the complete shared window; this
preserves H7's already-registered **minimum three months per lane**. A shorter
count is invalid and must not be accepted. T+1 fills and exit resolution may
occur after the last decision session. Final scoring waits until every
included decision is terminal and every included opening fill is closed; no
interim or incremental verdict is permitted.

## 4. Registration record to freeze before the first real tick

Stage 8 must first pre-register and independently review an exact activation
spec. Its first authorized forward-ledger event must be a new typed
`window_registration` event with no causes and at least:

- owner authorization identity/time and independent-review evidence;
- activation-spec SHA-256 and immutable code commit;
- canonical config hash and all Stage-4/5/6 frozen parameters;
- start decision session, session count, exact XNYS end rule, and proof that
  the final decision session satisfies the minimum three calendar months per
  lane;
- inclusive cohort rule keyed only by immutable decision session;
- Stage-6 scorer module/spec hash, `BOOTSTRAP_SAMPLES=5000`,
  `MIN_LOSSES_FOR_VERDICT=10`, and exact
  `SURVIVED | REJECTED | INCONCLUSIVE` mapping;
- the rule that `SURVIVED` is not live-trading approval or a profitability
  claim;
- current 12/12 source-health and 12/12 data-gate evidence identities;
- paid-data coverage evidence and the Darwin durability decision; and
- the verified pre-append state `VALID EMPTY`.

The event type and schema do not exist yet. Adding them, the guarded production
path, or any scheduler is Stage-8 implementation and is forbidden by this
readiness packet.

## 5. Atomic opening sequence — future Stage 8 only

1. Resolve/commit the unrelated working-tree changes; bind a clean commit and
   canonical config hash.
2. Restore source health to 12/12 with owner-reviewed provenance records.
3. Confirm paid daily EOD coverage through the full window plus lifecycle exit
   buffer.
4. Implement `F_FULLFSYNC` on Darwin or record the owner's explicit acceptance
   of the weaker durability guarantee.
5. Owner fills every §3 value, including the minimum-three-months-per-lane
   acknowledgement, and explicitly authorizes opening Stage 8.
6. Write and hash the exact Stage-8 activation spec; independently review it.
7. Test-first implement the registration schema and activation guard on
   synthetic stores; independently review and run the complete verification
   bundle.
8. Immediately before registration, rerun source health and Stage 2 for the
   latest completed session; require 12/12 on both and verify `VALID EMPTY`.
9. Append exactly one `window_registration` as the first real event and verify
   the chain. If any precondition changes, append nothing and remain inactive.
10. Start decisions only on the registered start session. Never backfill,
    substitute an earlier opportunity, or change the end date after outcomes
    are visible.

## 6. Daily and terminal stop rules

- Source health or data gate not 12/12: no board/decision output may be read;
  record only the authorized gate evidence once the Stage-8 schema permits it.
- Missing T+1 entry data: cancel-never-chase; terminal skip.
- Missing exit data: append the visible gap and retry the first later valid
  session under the frozen lifecycle.
- Any ledger verification, mirror reconciliation, capacity, schema, benchmark,
  or source-identity failure: stop; do not score or continue.
- Subscription coverage lapse: stop new decisions. Do not silently shorten,
  extend, or restart the registered window.
- Score exactly once after the registered decision window is complete and all
  included decisions are terminal. A result cannot authorize live orders;
  this repository remains a validator.

## 7. Present decision

**DO NOT OPEN STAGE 8.** Source health is 4/12, paid-data continuity is not
confirmed, Darwin durability is unresolved, owner window inputs are blank,
and the working tree cannot yet supply one immutable config/code identity.
The next authorized action is owner remediation/parameter entry—not a real
ledger append.
