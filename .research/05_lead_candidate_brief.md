# Brief — "OI change" context line for the attractiveness scanner (lead candidate C2)

**Status:** RATIFIED AS REVISED, 2026-07-25 (owner directive in session:
"use the table above and stand by those values"), after the adversarial
ratification review in `.research/06_ratification_review.md` returned REVISE.
The revision section at the bottom of this file supersedes the original
definition below wherever they conflict. Original text retained for history.
Implementation: Codex unavailable until 2026-07-28 (owner-stated), so the
owner directed implementation via Claude subagent with main-session review.
Scope ratified for immediate build is **v1 only** (signed delta line + UNKNOWN
taxonomy); percentile + NOTABLE are v2, gated on a pre-registered descriptive
calibration study per 06 §13.

Written 2026-07-25 as the decision-gate outcome for the strategy-enhancement
workflow (see `.research/decision.md`: gates 1–8 PASS, gate 9 routes
implementation through this brief instead of direct code). Style and standing
constraints follow the committed RQ2 briefs
(`docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md`); the
owner may fold this text into that document as a sixth brief.

## What (one sentence)

On each scanner card, show how much the chosen contract's open interest
changed since the prior session and how unusual that change is against the
same name's own trailing history — positioning *context*, displayed as a
neutral informational line, never a GREEN/RED grade, never a ranking input.

## Why (mechanism, with claim labels)

- **Official-source:** Pan & Poteshman (2006, *RFS* 19(3)) and Johnson & So
  (2012, *JFE* 106(2)) find informed-trading information in option VOLUME
  measures. **Inference (disclosed adaptation):** new positions must appear
  in open interest, so an unusual OI build-up at a specific strike is a
  mechanistically-adjacent, weaker proxy for the same positioning story; OI
  also moves on unwinds and market-maker inventory, which is why this ships
  as neutral context, not a directional signal.
- **Repo-verified:** the scanner uses OI today only as a static liquidity
  level (`passes_liquidity()`, five call sites in
  `options_researcher/attractiveness.py`); no change/flow measure exists
  anywhere, and no RQ2 brief covers it — genuinely orthogonal.
- **Repo-verified data:** zero new data. Historical per-contract OI is in
  every cached chain (`data/thetadata_adapter.py::CHAIN_COLUMNS`), documented
  look-ahead-free (prior-day ~06:30 ET OPRA report, adapter docstring lines
  14–17). Live `option_snapshot_open_interest` confirmed entitled and working
  in `reports/live_probe/2026-07-24.json`.

## Definition (frozen once owner types the values)

For the specific contract on a card (symbol, expiration, strike, right), on
evaluation session D with prior session D−1:

```
oi_delta_1d(D)  = OI(D) − OI(D−1)              # contracts; both values prior-known
oi_delta_pctl(D) = causal percentile of |oi_delta_1d(D)| within the trailing
                   window of that SAME contract-family's |oi_delta_1d| values
                   (window = OI_CHANGE_PCTL_WINDOW sessions, inclusive rank,
                   NaN until OI_CHANGE_PCT_MIN_OBS observations — the exact
                   convention `features.py::iv_rank` already uses)
NOTABLE flag     = oi_delta_pctl ≥ OI_CHANGE_NOTABLE_PCTL
                   AND OI(D−1) ≥ OI_CHANGE_MIN_BASE
UNKNOWN          = any input missing (no D−1 chain, contract absent, thin
                   history below min obs, or base below OI_CHANGE_MIN_BASE)
```

Display line on the card (exact wording test-pinned at implementation):
`OI Δ1d: +412 contracts (p97 vs own 1y) — NOTABLE build-up` or
`OI Δ1d: unavailable (UNKNOWN — <reason>)`. Never a GREEN/AMBER/RED grade.

## Proposed values — LLM-asserted, owner types the final numbers

| Constant (config.py) | Proposed | Reasoning |
|---|---|---|
| `OI_CHANGE_PCTL_WINDOW` | 252 | mirror `features.py` `PCT_WINDOW` (existing repo convention for "own 1-year history") |
| `OI_CHANGE_PCT_MIN_OBS` | 126 | mirror `PCT_MIN_OBS`; refuse (UNKNOWN) rather than estimate from thin history |
| `OI_CHANGE_NOTABLE_PCTL` | 0.95 | flag only tail events; percentile-vs-own-history avoids a hand-picked absolute contract count on a 15-name board with wildly different OI scales |
| `OI_CHANGE_MIN_BASE` | 100 | equals `MIN_OPEN_INTEREST`; a percentage jump on a sub-liquidity base is noise, and such contracts are RED-gated anyway |

## Files (implementation = Codex, from this brief)

- `config.py` — the four constants above (owner-typed).
- `options_researcher/attractiveness.py` (or a small helper module) — compute
  at card-build time from cached chains via
  `options_researcher/chains.py::load_range` over the trailing window;
  attach `oi_delta_1d` / `oi_delta_pctl` / `oi_change_status` fields to the
  card dict (NOT a `grades` key).
- `options_researcher/attractiveness_dashboard.py` — render the line in
  `_card_html`; UNKNOWN follows the existing fail-visible wording pattern.
- `tests/test_oi_change_line.py` — new file, offline unittest.

## Test plan (code correctness ≠ signal validity)

Code correctness (this brief): formula on hand-built frames; causal property
(truncating the chain cache at day D reproduces day-D values exactly — the
B1 truncation-test pattern); UNKNOWN on missing D−1 / absent contract / thin
history / thin base; zero-and-abnormal-OI handling; timestamp boundary (delta
uses D and D−1 evaluation sessions, never intraday snapshots); and the
standing RQ2 acceptance criterion: **board ordering and Top-3 selection
byte-identical with the line present vs. absent** (test-pinned).

Signal validity (explicitly NOT claimed): whether NOTABLE build-ups predict
anything is untested and stays untested until a separately pre-registered
descriptive study says otherwise. The display line makes no forecast and the
wording must not imply one.

## Non-goals

No ranking or hero-selection influence; no strike-cluster aggregation (v1 is
the card's own contract only); no put/call-ratio variant (C3 — depends on an
unverified `option_snapshot_trade` entitlement); no live-lane changes (the
line is computed from EOD cached chains only).

---

## RATIFIED REVISION — 2026-07-25 (supersedes conflicting text above)

Source: `.research/06_ratification_review.md` (full evidence and reasoning).
Owner ratified the review's parameter table by session directive 2026-07-25.

### Constants (config.py — all four frozen research settings, owner-ratified)

| Constant | Value | v1 status |
|---|---|---|
| `OI_CHANGE_MIN_BASE` | 100 | **ACTIVE** (LOW_BASE status) |
| `OI_CHANGE_PCTL_WINDOW` | 252 | frozen, INACTIVE until v2 calibration |
| `OI_CHANGE_PCT_MIN_OBS` | 126 | frozen, INACTIVE until v2 calibration |
| `OI_CHANGE_NOTABLE_PCTL` | 0.95 | frozen, INACTIVE until v2 calibration |

Additional mechanical constant (LLM-asserted, flagged to owner in the ship
report, not a strategy threshold): `OI_CHANGE_MAX_PRIOR_GAP_DAYS = 4` —
maximum calendar-day gap between evaluation session D and the latest prior
cached session for the delta to still be honest as "1d" (covers weekend and
single-holiday gaps; larger gaps go UNKNOWN as STALE_PRIOR_CHAIN).

### Superseding definition changes

1. **Reference set** for the v2 percentile is **selected-contract path
   history** (06 §6, design C), NOT the exact contract's own history — the
   original "same contract-family" wording is retired. (v2-only; recorded here
   so v1 code leaves room for it but implements none of it.)
2. **Timing**: the OI figure available on session D is economically as-of the
   close of D−1 (OPRA ~06:30 ET report). The display line must carry
   "as of prior close". "Δ1d" spans close(D−2)→close(D−1).
3. **Missing ≠ zero**: a contract absent from a cached day is CONTRACT_ABSENT
   (UNKNOWN), never a zero. Zero is a present row with `open_interest == 0.0`.
4. **UNKNOWN taxonomy (v1)**: `NO_PRIOR_CHAIN`, `STALE_PRIOR_CHAIN`,
   `GRID_SHIFT` (zero shared `(expiration, strike, right)` keys between the
   D and D−1 chains — corporate-action guard), `CONTRACT_ABSENT`, `LOW_BASE`
   (prior-session OI below `OI_CHANGE_MIN_BASE`). Check order:
   NO_PRIOR_CHAIN → STALE_PRIOR_CHAIN → GRID_SHIFT → CONTRACT_ABSENT →
   LOW_BASE → OK. `THIN_HISTORY` joins in v2.
5. **NOTABLE guard (v2)**: requires percentile ≥ threshold AND prior OI ≥ base
   AND `oi_delta_1d != 0` (inclusive-rank tie pathology, 06 §8).
6. **Display wording (v1, test-pinned verbatim)**:
   `OI Δ1d: +412 contracts (as of prior close)` /
   `OI Δ1d: 0 contracts (as of prior close)` /
   `OI Δ1d: unavailable (UNKNOWN — CONTRACT_ABSENT)`.
   Neutral typography; the word "build-up" is retired (directional flavor);
   no color coupling to sign; never a GREEN/AMBER/RED grade.
7. **Architecture**: the fields (`oi_delta_1d`, `oi_change_status`) attach in
   a dedicated pass strictly AFTER `rank_cards` (post-selection,
   post-ranking), making board invariance structural. The byte-identical
   board-ordering/Top-3 test from the original test plan is a merge blocker.
8. **Evidence relabel**: Pan & Poteshman (2006) and Johnson & So (2012) are
   PEER-REVIEWED INDIRECT (adjacent-only, volume not OI, underlying not
   contract level); no located literature studies contract-level 1-day OI
   change; the line claims to be an activity fact only (06 §2–§3).
