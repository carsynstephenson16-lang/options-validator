# Ratification review — OI-change context line (brief 05), four constants + Codex findings

**Date:** 2026-07-25. **Reviewer:** Claude (main session) with two Sonnet research
agents (repo/cache audit; literature/mechanics audit). **Scope:** adjudicate the
four proposed constants in `.research/05_lead_candidate_brief.md` and verify or
disband the seven Codex revision findings. No production code modified. One
read-only empirical characterization of the parquet cache was run (scratchpad
script, direct parquet reads, no strategy code, no OOS-gated path).

---

## 1. Executive verdict

**REVISE — decline ratification of the brief as written.** The feature concept
survives every architectural and data-availability check, but the brief's
percentile definition is ambiguous ("same contract-family") and, under its most
natural reading (the exact contract's own history), the proposed
`OI_CHANGE_PCT_MIN_OBS = 126` is **empirically counter-indicated**: 40%
eligible coverage in a 20-sample synthesis of the real selection rule, with 10%
of samples having zero prior observations at all. Codex's overall direction is
**verified** (5 of 7 findings verified, 1 verified-but-already-satisfied, 1
verified-problem-with-a-different-remedy). A revised brief with the reference
set fixed to selected-contract path history, timing wording corrected, and the
constants frozen as research settings can be ratified.

**Smallest safe scope (recommended):** ship v1 as the signed one-day delta line
only (`OI Δ1d: +412 contracts (as of prior close)`) with the full UNKNOWN
taxonomy — this needs **none** of the four constants except `OI_CHANGE_MIN_BASE`
— and gate the percentile + NOTABLE flag behind a separately pre-registered
descriptive calibration (notable rate, UNKNOWN rate, per-name distribution)
using the path-history design below.

---

## 2. Claim-by-claim evidence table (the brief's seven claims)

| # | Claim | Verdict | Evidence label |
|---|---|---|---|
| 1 | Pan & Poteshman / Johnson & So support informed-trading info in option **volume** | True for volume; **irrelevant as direct support for contract-level OI change**. P&P used *signed opening buy volume* from proprietary CBOE trade-classification data, underlying-level, 1-day/1-week horizon. J&S used the option/stock **volume ratio**, underlying-level, weekly. Brief's "Official-source" label is wrong — these are peer-reviewed papers. | PEER-REVIEWED INDIRECT EVIDENCE (adjacent-only) |
| 2 | Unusual OI growth is weaker, mechanistically adjacent context | Acceptable **only** as stated (disclosed inference). Closest real OI-change paper: Fodor, Krieger & Doran (2011, FMPM 25(3)) — **underlying-level aggregate** call/put OI changes, weekly horizon. No located paper studies a single contract's one-day OI change. | INFERENCE + PEER-REVIEWED INDIRECT |
| 3 | Historical per-contract OI is in every cached chain | True. `CHAIN_COLUMNS` includes `open_interest` (`data/thetadata_adapter.py:49-53`); docstring L14-17 documents the ~06:30 ET OPRA prior-close report. | REPO-VERIFIED |
| 4 | Live OI access works | True — `option_snapshot_open_interest` `ok: true` in `reports/live_probe/2026-07-24.json`. Caveat: the **live snapshot's** as-of semantics are documented nowhere in the repo (only the historical EOD endpoint's are). Moot for v1, which is EOD-only. | REPO-VERIFIED (with gap noted) |
| 5 | No new vendor dataset/entitlement | True for the EOD cached-chain path. | REPO-VERIFIED |
| 6 | Scanner uses OI only as static liquidity | True. Exactly 5 call sites, all `passes_liquidity()` grade badges computed **after** contract selection (`options_researcher/attractiveness.py:175-176, 232-233, 292-293, 334-335, 375-376`); ranking uses only `annualized_yield`/`breakeven_move` (`rank_cards`, L50-66). No OI change/flow measure exists anywhere. | REPO-VERIFIED |
| 7 | 252 / 126 / 0.95 / 100 are defensible | **Partially false.** 252 and 126 were mirrored from `features.py::iv_rank`'s `PCT_WINDOW`/`PCT_MIN_OBS` — an **underlying-level** daily series that exists every session. A specific contract does not: see §9. Mirroring is repo-consistent but not statistically valid for a per-contract series. | EMPIRICAL RESULT (against) + INFERENCE |

---

## 3. Corrected market mechanism (replaces the brief's "Why" paragraph)

Open interest counts contracts outstanding; every open contract has one long
and one short side by construction, so an OI increase means one new long **and**
one new short were created and can never reveal which side initiated
(OFFICIAL MARKET-MECHANICS EVIDENCE — OIC,
optionseducation.org/referencelibrary/faq/general-information: OI "indicates
neither a bullish nor bearish outlook"; four-case table confirmed: open+open →
+1, close+close → −1, open-vs-close → unchanged). The strongest honest claim:
the line is a **well-defined, once-daily, as-of-prior-close activity fact**,
shown the way a volume spike is shown — with no informativeness claim, because
no peer-reviewed paper studies this unit of analysis (single contract, one-day
OI change).

---

## 4. Point-in-time data definition (VENDOR-DOCUMENTED + REPO-VERIFIED)

- **report_available:** ~06:30 ET on evaluation session D (OPRA once-daily
  report; ThetaData docs, docs.thetadata.us/operations/option_history_open_interest.html).
- **economic_as_of:** close of session D−1. The figure available on D describes
  positions as of D−1's close.
- **oi_delta_1d shown on D** = report(D) − report(D−1) = economic change from
  close(D−2) to close(D−1). **The display must say "as of prior close"** — the
  brief's example wording omits this.
- OPRA **may send no OI message** for a contract ("might not be sent … if there
  is no open interest") — absence of a report is not a zero and not an
  unchanged value (VENDOR-DOCUMENTED). In the cache this maps to **row
  absence**: `_merge_chain_frames` inner-joins OI with greeks and drops
  contracts missing either (`thetadata_adapter.py:268-291`), and
  `validate_chain_schema` (L92-105) forbids NaN — so *missing = row absent;
  zero = row present with `open_interest == 0.0`* (REPO-VERIFIED; both cases
  observed in the real cache).
- No look-ahead: both inputs are prior-known reports; causality is inherited
  from the adapter design and must be pinned by a B1-pattern truncation test.

---

## 5. Repository findings (delta vs. the brief)

All of the brief's repo claims verified (see §2). Additional findings:

- `PCT_WINDOW`/`PCT_MIN_OBS` are hardcoded in `options_researcher/features.py:24-25`,
  **not** in `config.py` — a standing deviation from the every-number-in-config
  convention. The four new constants must go in `config.py` (brief already says so).
- `iv_rank`'s exact convention (`features.py:73-81`): current observation **is**
  included in the ranked window; percentile = `mean(window <= v)` — inclusive
  ≤ (ties count), empirical-CDF style, NaN until 126 finite obs in the trailing
  252-slot slice. (REPO-VERIFIED)
- Selection is by delta distance only, **before** any grade/field is built;
  RED-liquidity cards still display (not filtered); `rank_cards` sorts only on
  the passed `rank_key`. A post-selection card-dict field cannot mechanically
  feed selection or ranking today. (REPO-VERIFIED)
- No adjusted/non-standard-contract detection exists anywhere; contract identity
  is exactly `(expiration, strike, right)` (`_KEY_COLS`,
  `thetadata_adapter.py:243`) with no OCC root-symbol column. One real
  corporate-action collision mode was observed live (QQQ 2023-12-27
  dividend-adjusted strike mismatch → whole-day fail-closed skip,
  L302-312). (REPO-VERIFIED)

---

## 6. Contract-family decision (resolves the brief's ambiguity)

Three candidate reference sets for the percentile's trailing history:

- **A. Exact listed contract's own history — REJECTED.** Two independent
  defects. (i) Coverage: EMPIRICAL RESULT §9 — 40% of samples reach 126
  observations; 10% have zero (newly listed strikes: VST Aug-21-2026 $144P
  verified absent from cache before 2026-07-21 — strikes are listed
  progressively as spot approaches). (ii) Comparability: a contract's own life
  is nonstationary — the same contract was farther-dated and farther from the
  money months ago, so its old ΔOI distribution is not a valid baseline for
  today (listing-age bias + expiration effects + moneyness drift).
- **B. Matched cohort (underlying, right, DTE bucket, moneyness bucket) —
  REJECTED for v1.** Best comparability in principle, but introduces repeated
  observations per session, bucket-boundary artifacts, materially higher
  computation, and a bucket-design freedom that invites tuning. Reconsider only
  if the calibration study shows C is inadequate.
- **C. Selected-contract path history — ADOPTED (verifies Codex finding 1).**
  For each prior session s in the window, deterministically re-run the same
  card's selection rule on session-s data and take that day's selected
  contract's |ΔOI(s)|. One observation per session, coverage = symbol cache
  depth (VST/MSFT/AMZN ≥ 2150 sessions; CEG 1116; newer board names honestly
  UNKNOWN until 126 sessions), causal by construction, and the comparison
  distribution is like-kind (same delta/DTE character) by definition. Costs
  accepted: heavier compute (selection re-run per session over the window —
  feasible offline via `chains.py::load_range`), and regime drift if the
  selection rule's config changes (mitigation: the percentile is recomputed
  from current config each run and claims nothing beyond "unusual for what
  this card selects").

Consequence: the display comparison text changes from "vs own 1y" to
"vs this card's 1y" (exact wording in §12).

---

## 7. Exact formulas and status rules (revised definition)

For the selected contract on card role R, symbol S, evaluation session D:

```
oi_delta_1d(D) = OI_report(D) − OI_report(D−1)
    # both prior-known reports; economic span close(D−2)→close(D−1)
    # UNKNOWN if the contract row is absent on D or D−1 (absent ≠ zero),
    # or if the D vs D−1 chains show a strike-grid shift (corporate-action guard)

path history:  for each prior session s in the trailing OI_CHANGE_PCTL_WINDOW
    sessions, x(s) = |oi_delta_1d of the contract selected by (R, S) on s|,
    computed with only session-s-available data; skip s if that day is UNKNOWN

oi_delta_pctl(D) = mean( x(s) <= |oi_delta_1d(D)| )  over valid x(s) plus the
    current observation  # iv_rank convention: inclusive ≤, current obs included
    NaN until OI_CHANGE_PCT_MIN_OBS valid observations

NOTABLE(D) = oi_delta_pctl(D) ≥ OI_CHANGE_NOTABLE_PCTL
             AND OI_report(D−1) ≥ OI_CHANGE_MIN_BASE
             AND oi_delta_1d(D) ≠ 0        # zero-tie guard, see §8 (0.95 row)

UNKNOWN reasons (each displayed): NO_PRIOR_CHAIN, CONTRACT_ABSENT,
    THIN_HISTORY, LOW_BASE, GRID_SHIFT
```

Percentile convention: keep the repo's `iv_rank` inclusive-≤ rank (repo
consistency, already test-pinned there) — **not** Codex's midrank — with the
`oi_delta_1d ≠ 0` NOTABLE guard closing the tie pathology (see §8).

---

## 8. Parameter decisions (the four numbers — owner types the final values)

| Constant | Proposed | Verdict | Reasoning |
|---|---|---|---|
| `OI_CHANGE_PCTL_WINDOW` | 252 | **KEEP** (frozen research setting) | Coherent 1-year convention **under design C**, where path history is as deep as the symbol's cache. Repo-consistent; not empirically validated and doesn't need to be for a descriptive display. |
| `OI_CHANGE_PCT_MIN_OBS` | 126 | **REJECT under design A / KEEP under design C** (frozen research setting) | Under the exact-contract reading: EMPIRICAL RESULT — 8/20 samples reach 126 obs, 2/20 have zero; ~60% UNKNOWN makes the feature decorative. Under design C, 126 valid path sessions is routinely reachable for the four core names and honestly UNKNOWN for newly-added board names. |
| `OI_CHANGE_NOTABLE_PCTL` | 0.95 | **KEEP + NEEDS EMPIRICAL GATE** | Reasonable tail convention, but the realized NOTABLE rate on real data is unmeasured; the calibration study must report it before the flag ships. Tie pathology found: |ΔOI| has heavy mass at 0; with inclusive-≤ rank, a history that is ≥95% zero-change would let a **zero-change day** flag NOTABLE. Closed by the `oi_delta_1d ≠ 0` guard (§7) rather than by switching to midrank. |
| `OI_CHANGE_MIN_BASE` | 100 | **KEEP** (frozen research setting) | Equals `MIN_OPEN_INTEREST` (`config.py:125`); sub-base contracts are RED-badged anyway; percent-style noise on tiny bases suppressed. |

All four are **OWNER CHOICE / frozen research settings** — none is a validated
threshold, and the revised brief must say so (verifies Codex finding 6).

---

## 9. Empirical results (read-only cache characterization, 2026-07-25)

Method: direct parquet reads of `.cache/chains/{symbol}_{date}.parquet`;
selection rule synthesized exactly from `attractiveness.py`/`chains.py`
(nearest monthly 15–60 DTE, put nearest `H5_INCOME_DELTA=0.20`); 5 most recent
sessions × VST/CEG/MSFT/AMZN = 20 samples; exact `(exp, strike, right)` traced
across all prior cached sessions.

- Cache depth: VST 2018-01-02→2026-07-23 (2150 files); MSFT, AMZN same span;
  CEG 2022-02-09→ (1116 files, spinoff-limited).
- Exact-contract prior-presence counts (per sample): VST 0/1/120/121/124;
  CEG 0/1/2/142/143; MSFT 34/35/37/38/235; AMZN 233–237.
- Threshold coverage on |ΔOI| observations: **≥126: 8/20 (40%) · ≥60: 11/20
  (55%) · ≥20: 15/20 (75%) · zero obs: 2/20 (10%)**.
- Zero-obs root cause verified genuine (not a data gap): near-the-money strikes
  are listed progressively; VST $144P born 2026-07-21.
- Zero-OI days among present rows: 0–12 per sample; no NaN OI observed
  (consistent with the fail-closed adapter design).
- Not run (out of scope for a ratification review, required before NOTABLE
  ships): full-history causal replay, notable-rate/UNKNOWN-rate by name, right,
  DTE bucket, year; regime stability; correlation with existing card fields;
  card-order parity test. These form the pre-registered calibration study.

---

## 10. Failure modes

1. Newly listed strike → zero history (by construction, not a bug) — design C
   removes it from the percentile path; the **delta itself** is UNKNOWN only if
   D−1 is absent.
2. Missing OPRA message misread as zero/unchanged — prevented by row-absence
   semantics + CONTRACT_ABSENT status; must be test-pinned.
3. Corporate action shifts the strike grid → key mismatch or collision (no
   root-symbol column exists) — GRID_SHIFT guard day → UNKNOWN; full adjusted
   detection is impossible with the current schema (open gap).
4. Tie mass at zero + inclusive rank → zero-change NOTABLE — closed by the
   nonzero-delta guard.
5. Wording drift into a directional claim ("bullish build-up") — forbidden;
   display wording test-pinned (§12).
6. Future developer passes the new field as a `rank_key` or filter — the
   byte-identical board invariance test is the tripwire.

---

## 11. Required tests (adds to the brief's plan)

Brief's existing plan retained (formula on hand-built frames; B1 truncation/
causality; UNKNOWN taxonomy; zero/abnormal OI; timestamp boundary; **board
ordering and Top-3 byte-identical with line present vs. absent**). Additions:

- `absent ≠ zero`: a contract absent on D−1 yields CONTRACT_ABSENT, never Δ = OI(D) − 0.
- Zero-change-heavy history cannot flag NOTABLE (nonzero-delta guard test).
- Path-history percentile reproduces exactly under cache truncation at each s
  (causality of the per-session re-selection).
- GRID_SHIFT day yields UNKNOWN, not a spurious delta.
- Display wording pinned verbatim, including the as-of clause.

---

## 12. Revised display wording

```
OI Δ1d: +412 contracts (as of prior close · p97 vs this card's 1y) — NOTABLE
OI Δ1d: −85 contracts (as of prior close · p41 vs this card's 1y)
OI Δ1d: unavailable (UNKNOWN — CONTRACT_ABSENT)
```

Neutral typography; never GREEN/AMBER/RED; the word "build-up" is dropped
(directional flavor); no arrow icons.

---

## 13. Final implementation gate

1. Owner types the four constants into a revised brief (values per §8) — the
   revision adopts design C, the §7 formulas/status rules, §12 wording, and
   corrected evidence labels (§2, §3).
2. **v1 (implement first):** signed delta line + UNKNOWN taxonomy only.
   Constants needed: `OI_CHANGE_MIN_BASE` only (LOW_BASE status). No window,
   no min-obs, no percentile, no NOTABLE.
3. **Calibration study (pre-registered, descriptive):** causal replay over
   supported history reporting the §9 "not run" list. No return prediction —
   this field is descriptive, not an alpha signal.
4. **v2:** percentile + NOTABLE ship only after the calibration study's
   numbers are reviewed and the remaining three constants are owner-frozen.
5. Codex implements from the revised brief; tests per §11; board-invariance
   test is a merge blocker.

## 14. Open evidence gaps

- No peer-reviewed literature at this unit of analysis (single contract,
  one-day OI change) — searched, not exhaustively canvassed; the display may
  claim nothing beyond "activity fact."
- OCC's own publication-timing page could not be fetched directly (HTTP 403);
  timing rests on OIC + ThetaData vendor docs (consistent with each other).
- Live snapshot OI as-of semantics undocumented in repo (moot for EOD-only v1).
- Adjusted-contract identification impossible with current schema (no root
  symbol) — permanent limitation, disclosed.
- Exact sample periods of the three cited papers unverified (paywalled).

---

## Codex findings — verdicts

| # | Codex finding | Verdict |
|---|---|---|
| 1 | "Same contract-family" → selected-contract path history | **VERIFIED — adopted** (§6). Exact-contract history fails on coverage *and* comparability. |
| 2 | Separate report-arrival from economic as-of date | **VERIFIED — adopted** (§4); display must carry the as-of clause. |
| 3 | Distinguish missing messages from genuine zero changes | **VERIFIED — adopted**; vendor-documented (OPRA may send nothing) and repo-verified (missing = row absent; zero = row present at 0.0); pinned by test. |
| 4 | Percentile → causal midrank | **PROBLEM VERIFIED, REMEDY REVISED**: the tie pathology is real, but the fix is the nonzero-delta NOTABLE guard + keeping the repo's test-pinned iv_rank inclusive-≤ convention, not a second percentile convention in the codebase. |
| 5 | Scope to standard, unadjusted contracts | **VERIFIED — adopted** as GRID_SHIFT guard + disclosed limitation; full detection impossible without root-symbol data. |
| 6 | Four parameters = frozen research settings, not validated thresholds | **VERIFIED — and strengthened**: 126 under design A is not merely unvalidated, it is empirically counter-indicated (40% coverage). |
| 7 | Attach field only after contract selection | **VERIFIED but already satisfied**: selection precedes all field computation and ranking reads only `rank_key` (repo-verified); retained as the byte-identical invariance test, no architectural change needed. |
