# Event-edge signal — promotion from parking lot into a phase

**Date:** 2026-07-15
**Authorization:** explicit owner instruction this session ("take the very best
idea from ideas parking lot and bring it into a phase. rate it off probability
and profitability"). The parking lot's own pull condition — "an explicit owner
decision" — is met; the pull is logged in `ledger/facts.log`
(EVENT_EDGE_UNPARKED). The first-verdict standing rule is overridden by that
owner decision for THIS item only, mirroring the H7 SCOPE_OVERRIDE precedent
(2026-07-09).

## Rating of the parked ideas (as of 2026-07-15)

"Probability" = chance the item reaches decision-grade output with current
data and repo machinery. "Profitability" = expected impact on the live arc's
eventual after-cost expectancy (all such impact is indirect until a hypothesis
survives its window — nothing here is edge). Both are Inference, labeled as
such; no number below is a backtest output.

| Parked idea | Probability | Profitability impact | Why not the pick |
|---|---|---|---|
| **Event-edge signal (implied vs realized event move)** | **High** — data already cached (chains + confirmed earnings dates for the H6 names), mechanical, offline | **High (indirect)** — directly prices the owner's new pre-earnings interest: it measures whether the event vol being bought is rich or cheap, and how crush/run-up behave by tenor | **PROMOTED** |
| Market-implied probability readout | High — cheap, display-only | Low — informational, gates nothing | Strong runner-up; fold in later as a display |
| Term-structure signal (IV30/IV90) | Medium — needs a second ATM tenor in the feature layer first | Medium — overlaps event-edge partially | Blocked behind feature work; event-edge subsumes the event-window part |
| Richness badges (VIXEQ-based) | Low — no VIX/VIXEQ feed exists | Low-medium | Data blocker unresolved |
| Drawdown-reversal scanner | — | — | Substantively absorbed into registered H7a; unparking would duplicate a live lane |
| TradingView / Pine layer | Low here | Low | Routed to equity-research repo by prior decision |
| Qullamaggie momentum port | Low — needs OHLCV universe + screener + heavy anti-look-ahead work | Unknown | Gate unchanged (first verdict); risk of scope explosion |
| Non-AI diversification names | High (research) | Unknown | Just parked 2026-07-15; ticker choice is an owner decision with a data cost |
| AVGO SPLITS entry | Done — registered 2026-07-15 (commit 7c9bab7) | — | Already complete; should be struck from the lot |

## The phase

**Phase E1 — descriptive event-vol study (active now).** Measure, from cached
chains only: implied move at T-1 vs realized move per past earnings event;
ATM-IV run-up into the event by tenor bucket (14–30 DTE vs 45–90 DTE); crush
at T-1→T+1 by tenor; half-spread costs by tenor; contract-level price paths
(no entry/exit rule, no P&L — descriptive only, per the H6 registration's
"descriptive history as context, never verdict" clause). Names: NVDA/PLTR/AMZN
(+ AMD/AVGO/SMCI where cache depth allows). Deliverable: dated report in
`reports/`. No pre-registration needed BECAUSE it grades and ranks nothing.

**Phase E2 — gate (NOT active).** If the owner wants event-edge to *gate or
rank* anything (e.g., "only enter pre-earnings when implied move ≤ X× the
median realized move of the last N like events"), that is a hypothesis
parameter: it requires owner-typed numbers pre-registered in the ledger before
it influences a single entry. The E1 report must propose the candidate
definitions (event window, N, implied-move source) in a table for the owner to
fill — per the parking-lot gate written 2026-07-06 and standing rule 3
("you own the numbers").

**Relation to the live arc:** E1 feeds the owner's requested pre/post-earnings
plan (see `docs/superpowers/specs/2026-07-15-pre-post-earnings-plan.md`) and
the design of a possible pre-earnings hypothesis (H8 candidate). It changes no
H5/H6/H7 parameter.
