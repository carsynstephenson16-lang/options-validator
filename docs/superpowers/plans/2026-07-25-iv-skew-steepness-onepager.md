# IV skew steepness (OTM-put skew slope) badge — owner-approval one-pager

**Date:** 2026-07-25. **Status:** DRAFT spec for owner nod; nothing registered,
nothing built. Companion to the parked entry in `ideas-parking-lot.md`
("IV skew steepness (OTM-put skew slope) badge", parked 2026-07-25) and
`.research/03_strategy_candidates.md` §C4 (score 24/30, runner-up). Follows
the N3-1 "owner-nod one-page spec" path used in
`docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md`.

**Scope guard:** this is a display-only badge on the existing 15-name
scanner board. It moves no live hypothesis toward its verdict by itself; it
is gated exactly as parked — an owner-approved convention freeze BEFORE any
result is computed, plus this external-validity memo. If approved, it
queues behind Phase-1 recorders like every other RQ2 candidate.

## 1. Plain-English what and why

**Implied volatility (IV)** is the market's own guess, priced into an
option's premium, of how much a stock will swing before expiration.
**Delta** here is used as "how far out-of-the-money a strike is": a
0.50-delta put sits at-the-money; a 0.25-delta put is further below the
current price (roughly a 1-in-4 chance of finishing in the money). **Tenor**
just means days-to-expiration (DTE).

On most stocks, downside-protection puts trade at a *higher* IV than
at-the-money options — investors pay up for crash insurance. The **skew
slope** is simply the size of that gap: (IV of an out-of-the-money put) minus
(IV at-the-money), at one snapshot in time, one tenor. A steeper gap means
the market is pricing more relative fear into the downside. The proposed
badge would just display that number and its trend — it does not say "buy"
or "sell," and it does not touch any existing grade.

## 2. Three candidate frozen conventions

All three reuse the existing 15–60 DTE nearest-monthly window
(`chains.nearest_monthly`, min_dte=15/max_dte=60) that `atm_iv` already uses
(**Repo-verified**, `options_researcher/features.py:4`, `chains.py:61-63`),
so the skew leg and the ATM leg always share one expiration by construction.

| # | Candidate definition | Pros (this repo's data reality) | Cons (this repo's data reality) |
|---|---|---|---|
| 1 | `skew_25 = iv(0.25Δ put) − atm_iv`, same nearest-monthly expiration; `atm_row(chain, exp, target_delta=0.25)` (**Repo-verified** function signature, `chains.py:94-96`, default `target_delta=0.50`) | One-line reuse of the exact function/tenor already used for `atm_iv`; 0.25Δ is the delta point most commonly quoted as "the" skew in vol-surface writeups (**Inference** — not verified against the exact delta Xing/Zhang/Zhao (2010, JFQA) used) | Further-OTM strikes carry thinner open interest on this 15-name board; both legs must each clear `MIN_OPEN_INTEREST=100` and `MAX_SPREAD_PCT=0.10` (**Repo-verified**, `config.py:125-126`) — expect more honest no-data days than a milder delta |
| 2 | `skew_20 = iv(0.20Δ put) − atm_iv`; `atm_row(..., target_delta=0.20)` | 0.20 is the *exact* delta this repo already targets for real income strikes — `H5_INCOME_DELTA=0.20` with a `±0.15` band `H5_INCOME_DELTA_BAND` (**Repo-verified**, `config.py:295-296`); badge would show skew at the strike H5 would actually consider selling | Even further OTM than #1 → same liquidity concern, somewhat worse; drifts further from whatever specific delta the source paper used (**Not-found** — the paper's exact strike/delta convention was not located in this repo's notes), weakening precision of the PEER-REVIEWED INDIRECT citation |
| 3 | `skew_pct = iv(nearest strike ≤ X% of spot) − atm_iv`, no delta solve, same expiration | Sidesteps any name-day where the `delta` field itself is missing/unhealthy — a distinct hedge from the liquidity gates; simplest definition to explain | Needs new nearest-strike-below-threshold selection logic, not a one-line reuse of `atm_row`'s delta-matching; a fixed %-OTM point sits at a *different* delta for a high-IV name than a low-IV name, so cross-name/cross-day comparisons mix moneyness with vol regime — the weakest match to the mechanism the paper describes (**Inference**) |

## 3. Recommendation (values still owner-typed)

Recommend **candidate 1 (0.25Δ)** as the primary convention: cheapest to
build (identical `atm_row` call pattern to the existing `atm_iv`, differing
only in `target_delta`), and closest to the delta point most vol-surface
literature treats as canonical. The liquidity con is real and should not be
papered over — per repo law (skip-and-log, `.cursorrules`), a day where
either leg fails `MIN_OPEN_INTEREST`/`MAX_SPREAD_PCT` renders an honest gap,
never a fallback substitution.

Values to freeze as **[OWNER]** before any code runs:
- **[OWNER: which candidate — 1, 2, or 3]**
- **[OWNER: exact delta target if 1 or 2, or exact %-OTM threshold if 3]**
- **[OWNER: raw slope only, or also a causal percentile]** — if a percentile
  is wanted, reuse the Brief B1 pattern already spec'd (trailing 252 obs,
  min 60, lookahead-excluded rows labeled/excluded) rather than inventing a
  second window convention
- **[OWNER: fallback on liquidity-gate failure]** — recommend "honest gap,
  no fallback delta," consistent with repo law

## 4. External-validity memo (small-universe caveat)

Xing, Zhang & Zhao (2010, *JFQA*) is **PEER-REVIEWED INDIRECT**: an
underlying-level, cross-sectional result across several hundred individual
equities, finding that steeper single-name put-IV smirks predicted lower
future returns for *that* stock, over *that* broad sample. It is not a
time-series signal tested on any one name, and it is not tested on a
14–15-name, single-thesis, AI-infrastructure-correlated board. Applying a
many-hundred-stock cross-sectional pattern to this board's own history is an
out-of-sample extrapolation the original paper does not itself make or test.
The badge must be framed as "this is what the skew looks like," never as
"this predicts a move" — any predictive framing would need its own
registered, forward-tested hypothesis, not a display badge.

## 5. Non-goals

- Display badge / prose line only — **never** enters a grade, rank, board
  ordering, or entry trigger for any hypothesis (H5/H6/H7/H8 or RQ2).
- **No directional claim.** The badge states a number (and, if approved, a
  percentile); it does not say "bearish," "bullish," "cheap," or "rich."
- Not a new scanner, suggestor, or optimizer — an additive column on the
  existing frozen board, same guard as every other RQ2 badge brief.

## 6. Pre-registration checklist (order matters)

1. Owner approves this one-pager and fills the **[OWNER]** blanks in §3.
2. Convention is entered into the ledger (`ledger/`) as a frozen definition
   — parameters recorded BEFORE any value is computed on real data.
3. Only then is the badge computed, tested (causal-percentile property test
   if a percentile is included; frozen-recipe byte-identical pin matching
   B1/A1/C1/N3-1/V1), and rendered.
4. Any later change to the delta/strike/tenor choice is a new registration,
   not an edit to this one — same discipline as every other frozen number
   in this repo.
