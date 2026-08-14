# Attractiveness-scanner experiment program — authorization record (2026-08-09)

**Provenance:** owner-directed, in-session, 2026-08-09. The owner's session
directive commissioned a bounded program of three to five parking-lot
experiments for the attractiveness scanner and instructed that the smallest
consistent authorization be recorded in the authoritative rule files.
Recorded by Claude Fable 5 (orchestrator); research by Claude Sonnet 5
subagents; implementation is Codex-only per the standing division of labor.

## 1. Rule state verified before any edit

- `.cursorrules` (Scope guard) — carries the 2026-08-03 owner-directed
  amendment: "the pre-verdict ship-blocker is retired repo-wide; the
  scope-guard question above no longer blocks building." Verified present
  exactly once before editing.
- `AGENTS.md` — carries the same 2026-08-03 amendment in matching wording.
  Verified aligned with `.cursorrules` before editing (`grep -c "ship-blocker
  is retired"` = 1 in each file).
- `PROJECT_STATE.md` (canonical roadmap, audit 2026-08-02 + directive update
  2026-08-03) — records the same retirement; its P0 queue is closed
  (P0.1–P0.6, P0.8) and nothing in its §6 still-blocked list covers
  display-only scanner work.
- `CLAUDE.md` (user-global manual) — amendment of 2026-08-03 retiring the
  ship-blocker is recorded there by the owner. Not edited in this program.

**Conclusion:** the old blocker was already retired on 2026-08-03. It was NOT
re-retired, deleted, or reworded by this program. No conflicting wording was
found that required correction; what the authoritative files lacked was a
recorded authorization for THIS named program, which is the only thing added.

## 2. The narrow authorization (as recorded)

Owner-directed attractiveness-scanner experiment authorization, 2026-08-09:

The global pre-verdict ship-blocker remains retired. The owner authorizes a
bounded program of three to five selected parking-lot experiments for the
attractiveness scanner. Each experiment remains display-only, disabled by
default, cached-data-only, causally timed, and stamped with its maximum as-of
session. Experiments must remain isolated from registered hypotheses, verdict
authority, FIRE authority, live-order paths, paper-book mutation, and the
default baseline ranking. Each experiment requires a dated specification,
isolated output, named acceptance metrics, tests, failure behavior, and a
rollback path. Promotion beyond experimental status requires a separate owner
decision and every applicable registration or feasibility gate. Existing hard
guardrails, provider restrictions, append-only records, owner-only frozen
values, and no-live-order rules remain unchanged.

What this authorization is NOT: it is not authorization for live trading,
spend, new accounts, provider calls, credential creation, holdout reveals,
ledger registrations, frozen-number invention, or any scope expansion beyond
the named program.

## 3. Constants policy (pre-empting the survey's "owner-typed constants" gate)

The 2026-07-22 quant-methods survey's common gate for parked ranks 7–20 reads
"ships display-only, fail-closed, owner-typed constants; entry into ranking
only via an RQ2-class registration." This program resolves that as follows,
per the composite-lane precedent (2026-08-04 decision report and the
2026-08-04 staleness-gate shipping, both of which shipped display-only
capability on constants "standard-from-literature, frozen in config.py with
LLM-proposed provenance"):

- Display-only experiment constants are standard-from-literature or
  official-source conventions, frozen in `config.py`, labeled with
  LLM-proposed provenance and the date. They are never silently promoted.
- The "owner-typed" requirement binds at PROMOTION into any grading, ranking,
  gating, or registered study — exactly where the survey's own gate places
  ranking entry ("only via an RQ2-class registration").
- Any experiment whose OWN gate demands an owner-typed value or a ledger
  registration before code exists is disqualified from this program
  (applied: IV-skew-steepness one-pager with unfilled [OWNER] blanks;
  HAR-RV/EWMA/GARCH registered-study-first gate; OI-change v2
  registered-calibration-study gate).

## 4. Files changed for this authorization

1. `.cursorrules` — one paragraph appended at the end of the Scope guard
   section (after the 2026-08-03 amendment). No other line touched.
2. `AGENTS.md` — the same paragraph inserted at the mirrored position (after
   "Hard guardrails, claim discipline, and vocabulary discipline are
   unchanged.", before the Registration feasibility gate paragraph). No other
   line touched.
3. `CLAUDE.md` and `PROJECT_STATE.md` — deliberately NOT edited: neither
   restates per-program scope exceptions (CLAUDE.md imports `.cursorrules` as
   the authoritative wording; PROJECT_STATE.md defers scope registry to
   README/ledger), so no authority conflict exists without an edit.

## 5. Hard guardrails preserved (unchanged, verified after edit)

No look-ahead; conservative fills (mid or worse + slippage haircut); costs on
both legs; liquidity gates; EOD-gap skipping; cache immutability; no provider
endpoint call without owner approval; offline tests; append-only ledgers via
typed APIs only; sealed legacy holdout (0/3 reveals); owner-only frozen
numbers for registered hypotheses; validator-only — no live orders, no
live-order code paths, hooks stay enforced; claim discipline and vocabulary
discipline. The registration feasibility gate (2026-07-24) continues to bind
every future promotion.

## 6. Registry facts this program must respect (read before implementing)

- `ledger/experiments.jsonl` seq 18 (RQ2-v1): K=2 badges frozen — Badge B
  (term-structure/VRP corner) and Badge A (bounce lens); forward window opens
  2026-09-01; badge modules not yet built. This program must not build,
  modify, or duplicate those badges.
- `ledger/experiments.jsonl` seq 19 (A2-v1): after-cost outcome battery on the
  frozen GREEN-fraction ranking; not yet built. Untouched by this program.
- Discrepancy surfaced for the owner (NOT resolved here): the RQ2 briefs doc's
  delegated-values table says K=3 including V1 (VRP calibration), but the
  chained registration (seq 18) says K=2 and omits V1. Owner adjudication
  needed before anyone treats V1 as registered.
- The frozen GREEN-fraction baseline ranking (RQ1 recipe) is the baseline lane
  of this program and is not modified while experiment flags are off.

## Addendum 2026-08-10 — K discrepancy resolved; seq-18 date attribution corrected

*Appended 2026-08-10; the original text above is unchanged (dated report,
append-only).*

- **K discrepancy RESOLVED.** The §6 discrepancy bullet is no longer open:
  ledger seq 25 (`RQ2_AMENDMENT_V1_1`, 2026-08-10, owner-directed) adjudicates
  RQ2-v1 to **K=3 candidate badges — B1, A1, V1** — with V1 registered as
  **membership-only** (its candidate statistic is NOT pinned; the RQ2 runner
  must refuse any V1 comparison until a further pre-result append-only
  amendment pins it). Read seq 25 in `ledger/experiments.jsonl` before
  treating V1 as anything more than a registered member.
- **Attribution correction.** §6 attributes "forward window opens 2026-09-01"
  to ledger seq 18, but seq 18 contains no start date. That date comes from
  the LLM-proposed delegated-values table in
  `docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md`
  ("RQ2 forward window | Start 2026-09-01; backstop 2027-09-01"), not from the
  chained registration.
