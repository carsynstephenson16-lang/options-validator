# OI-change v2 calibration study — design (not run)

**Date:** 2026-07-25. **Status:** DESIGN ONLY — no code, no run. This is the
pre-registered protocol required by `.research/06_ratification_review.md`
§13 step 3 before the OI-change line's v2 (percentile + NOTABLE flag) can
ship. v1 (signed delta + UNKNOWN taxonomy) is already implemented
(`options_researcher/oi_change.py`) and unaffected by this document.

**Plain-English lead.** Today the scanner shows "open interest changed by X
contracts since yesterday." v2 would add: "and that's unusually big compared
to what this same card normally shows," plus a flag for the top 5% of days.
Before that ships, we must first measure — on real historical data — how
often it would fire and whether it behaves sanely. This is NOT "prove it
predicts anything"; it explicitly makes no such claim. This document is the
measurement plan; the measurement itself is a later, separate step.

---

## 1. Replay protocol

**Design adopted:** selected-contract path history (06 §6 design C) —
**Repo-verified** ratified choice (`05_lead_candidate_brief.md` RATIFIED
REVISION item 1; `06_ratification_review.md` §6, §13.1).

For each `symbol` in `config.ATTRACTIVENESS_UNIVERSE` (15 names) and each
`card role` (the five existing row-builders in `attractiveness.py`:
`put_card_rows`, `cc_card_rows`, `pmcc_card_rows`, `leaps_card_rows`,
`long_call_card_rows` — **Repo-verified**), and each cached session `D` in
that symbol's history (`.cache/chains/{symbol}_*.parquet`; depth varies —
VST/MSFT/AMZN ≥2150 sessions, CEG 1116, newer board names shorter,
**Repo-verified**, 06 §9):

1. Re-run the role's existing selection rule using **only session-`D`-known
   data** — call the row-builder on `load_range(symbol, D, D)[D]` exactly as
   the live scanner would that day. No new selection logic; import and call
   the existing functions read-only. `attractiveness.py` is never edited.
2. From the selected `(expiration, strike, right)`, compute `oi_delta_1d(D)`
   by reusing `oi_change.oi_change_fields` unchanged (same UNKNOWN taxonomy,
   same absent≠zero semantics) against `find_prior_chain(symbol, D)`.
3. Build the trailing path history: for each prior session `s` in the
   `OI_CHANGE_PCTL_WINDOW=252` window, repeat steps 1–2 **as of `s`** (select
   the card that session's data would have produced, not today's contract
   projected backward) and take `|oi_delta_1d(s)|`; skip `s` if not `OK`.
4. `oi_delta_pctl(D) = mean(x(s) <= |oi_delta_1d(D)|)` (iv_rank inclusive-≤
   convention, **Test-verified** pattern) once ≥ `OI_CHANGE_PCT_MIN_OBS=126`
   valid `x(s)` exist, else NaN/`THIN_HISTORY`.
5. Would-be `NOTABLE(D)` under the frozen constants (`NOTABLE_PCTL=0.95`,
   `MIN_BASE=100`, nonzero-delta guard) — **display value only, never
   written back to any card or store.**

**Causality requirements:**
- **Truncation property (B1 pattern):** re-running the replay with the cache
  truncated at any `T <= D` must reproduce `D`'s `oi_delta_pctl`/`NOTABLE(D)`
  byte-identically — the causal proof 06 §11 requires; pin as a synthetic-
  frame unit test, not re-derived per symbol in the big replay.
- Each `s` must use the card **that session** would have selected — a
  same-contract shortcut anywhere silently reverts to rejected design A.
- Grid-shift/corporate-action days skip via the existing `GRID_SHIFT`
  status, never patched over.

**Code reuse vs. fresh:**
- **Reused unchanged:** `chains.py::load_range`/`nearest_monthly`/`atm_row`,
  the five `attractiveness.py` row-builders, all of `oi_change.py`.
- **Written fresh, research-only:** `analysis/oi_v2_calibrate.py` — the
  replay loop above, the percentile/NOTABLE computation (specified in 06 §7
  but implemented nowhere yet), and the §2 report aggregation. **Never
  imports from or writes to `attractiveness.py`, `attractiveness_dashboard.py`,
  or any live/scanner path** — reads the cache directly, writes only to
  `reports/oi_v2_calibration/`.

---

## 2. Report deliverables (exactly the §9 "not run" list)

One dated report `reports/oi_v2_calibration/{run_date}.md` + machine `.json`
(precedent: `reports/rq1/`):

1. **Eligible-card coverage** — fraction of (symbol × role × session) cells
   with a selectable card.
2. **UNKNOWN rate + reason mix** — by `{NO_PRIOR_CHAIN, STALE_PRIOR_CHAIN,
   GRID_SHIFT, CONTRACT_ABSENT, LOW_BASE, THIN_HISTORY}`.
3. **NOTABLE rate** — overall, and by symbol, `right`, DTE bucket, year.
4. **Stability across vol regimes** — split by high/low realized-vol
   (median-split on `features.py::rv21` is sufficient).
5. **Expiration/new-listing concentration** — NOTABLE fraction near roll
   dates or a strike's first cache appearance (VST $144P-type case, 06 §9).
6. **Sensitivity table** (descriptive only, parameters stay frozen):
   `WINDOW ∈ {126,252,504}` × `MIN_OBS ∈ {63,126}` × `PCTL ∈ {0.90,0.95,0.99}`
   × `MIN_BASE ∈ {50,100,250}` — NOTABLE rate + coverage per cell as context,
   **not** a search for a "better" cell; the frozen row (252/126/0.95/100)
   must be visibly marked.
7. **Correlation with existing card fields** — Spearman rho vs.
   `passes_liquidity()` grade, `iv_rank`, volume-less flag (skip with a
   stated reason if no such proxy exists — no fabricated one).
8. **Stale/repeated-report rate** — identical `oi_delta_pctl`/NOTABLE state
   on consecutive sessions per `(symbol, role)` (catches a stuck computation).

---

## 3. Pre-registration discipline

**DESCRIPTIVE, not a verdict-bearing hypothesis.** No returns, no forward
outcomes, no alpha claim: the OI-change line is a **display field**, never a
signal or trigger (scope-guarded, 06 §10 #6; the byte-identical board-
invariance test is a merge blocker regardless of this study's numbers). This
study cannot reject/promote a profitability claim — only judge whether the
*display* behaves sanely (coverage, NOTABLE frequency, no stuck states).

**Ledger writes (before running):** a `trial_intent` entry,
`hypothesis_id: "OI-V2-CALIB"`, `reason` quoting the frozen constants
verbatim (window 252 / min-obs 126 / pctl 0.95 / base 100 / max-gap 4) plus
this doc's path, following the RQ1 precedent (`ledger/experiments.jsonl`
seq 17). `context_sha256` = `sha256_file` of this design doc (reusing
`research.hashing.sha256_file`, the helper `rq1_runner.py:230-233` already
uses) so the protocol is hash-pinned before any number exists. Each run then
appends a `retrospective_result` with `prereg_ref_sha256` = that
`trial_intent`'s `record_hash` (RQ1 seq 20 linkage pattern), `labels:
["descriptive-only", "no-verdict", "cannot-promote"]`, and the §2 report by
path + hash.

**One-run or re-runnable? Recommend: re-runnable, ledger-logged every run.**
Precedent: RQ1 (`ledger/experiments.jsonl` seq 17/20) is a descriptive,
no-verdict study run under identical reasoning ("no rho is ever edge without
a fresh forward preregistration"). Unlike H7/H9/H6, which spend a scarce
one-shot inferential budget (a real trade or a frozen backtest verdict),
this study spends nothing "usable up" — each re-run (e.g. after a cache
refresh) is a fresh honest measurement of a non-decision-bearing quantity.
The one-run contract exists to stop p-hacking a verdict; there is no verdict
here to hack.

---

## 4. Acceptance gate for shipping v2 display

Owner reviews §2 against these before the three INACTIVE constants flip to
ACTIVE. All numeric bands are **[OWNER]** blanks — proposals only, not
defaults:

| Condition | Gate |
|---|---|
| Eligible-card coverage (2.1) | ≥ **[OWNER]%** of cells produce an `OK` card |
| UNKNOWN rate, core names (VST/CEG/MSFT/AMZN) | ≤ **[OWNER]%**; reason mix mostly `THIN_HISTORY` confined to each symbol's first ~126 sessions (a late-window spike flags a bug, not thin history) |
| NOTABLE rate overall | within **[OWNER]–[OWNER]%** (sanity band around the nominal ~5% implied by `NOTABLE_PCTL=0.95`) |
| Stale/repeated-report rate (2.8) | ≤ **[OWNER]%** consecutive-identical sessions per card |
| Sensitivity table (2.6) | context only, no gate; owner confirms the frozen row isn't a pathological outlier among the 36 cells |
| Truncation/causality unit test | must PASS unconditionally — correctness, not calibration, so not owner-tunable |

If a non-test gate fails, the finding is "v2 needs a different reference
design or parameter" (back to 06 §6 design B reconsideration) — never
silently reworked to pass; the frozen constants stay frozen either way.

---

## 5. Compute/runtime estimate and offline constraint

**Offline, cache-only, no network** — every input is already-cached parquet
(`.cache/chains/`, 2.9 GB / ~30k files, **Repo-verified**); touches no paid
ThetaData path and must run identically with the terminal offline.

**Estimated runtime (Assumption, not measured):** dominant cost is the
per-session re-selection inside the 252-session trailing window, repeated
per evaluation day: 15 symbols × 5 roles × up to ~2150 sessions × up to 252
inner replays ≈ low tens of millions of row-builder calls worst case (each a
millisecond-scale single-session filter) — likely a multi-hour batch job,
not seconds. Recommend caching each `(symbol, role, session)` `x(s)` value
once (reusable across overlapping windows) rather than recomputing per
inner loop, and starting with the four core names before the full 15-name
board to bound first-pass runtime.

---

## What I could not verify

- No literal `"role"` field was found on card dicts; "card role" refers to
  the five row-builder functions — the same abstraction 06 uses (`(R, S)`
  notation) without pinning a dict key. **Inference**, not confirmed.
- Per-symbol cache depth for the newer H7 watchlist names (CRWV, TEM, PLTR,
  NOW, SMCI, NVDA, AMD, AVGO, IREN, USAR, ET) was not re-measured here; only
  the four core names' depths are stated in 06 §9.
- §5's runtime estimate is order-of-magnitude only — no code was executed
  for this document, per the task's design-only scope.
