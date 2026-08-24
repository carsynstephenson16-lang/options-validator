# Fill-adversity context study (descriptive) — Codex brief

- **Date:** 2026-08-24
- **Author:** Claude Fable 5 orchestrating session
- **Executor:** Codex (default model, high reasoning)
- **Status:** rev 3 — two independent adversarial review rounds (Opus,
  2026-08-24). Rev 1 FAILED (circular headline measurement, finding 3). Rev 2
  replaced the design; round-2 review verified the redesign non-circular but
  returned PASS WITH FIXES: R2 ("adverse" mislabel — 45% of |Δmid| is
  favorable), R3 (saturated headline fractions: 67%/98%), R4 (seq-21
  comparison wrong on scope and sidedness; two-leg effect measured 4.5×),
  R5 (unfalsifiable success criterion), R9 (|delta| bands don't cover >1/NaN)
  — all applied in this revision, plus minors R6–R8, R10–R12. Ready for
  hand-off; merge timing stays with the owner.
- **Provenance:** Repo-verified against local HEAD `24368f6` unless labeled
  otherwise; review measurements (flood/staleness/bucket/drift/saturation
  numbers quoted below) were computed read-only on the real caches
  2026-08-24 by the reviewing agent. Parent plan:
  `docs/plans/2026-08-24-options-validator-research-integration-plan.md` §6
  Phase 2 (WS-1). **Owner ruling 2026-08-24 (in-session, verbatim): "yes to
  chains_v2 read-only" — Tier-2 read-only research access to
  `.cache/chains_v2/od1-2026-08-01/` is APPROVED for this study. Read access
  only: no merge of `codex/od1-v2-current`, no verdict eligibility, the
  quarantine stands.**

## Why this exists (plain language)

Every verdict-bearing cost model assumes fills at the touch plus a 1% adverse
haircut (`config.SLIPPAGE_HAIRCUT = 0.01`, `config.py:91`; applied in
`strategies/base.py:12-97`; identity-frozen as `FILL_MODEL_ID =
"conservative_bid_ask_plus_haircut_v1"`, `config.py:237`, hashed via
`research/hashing.py:53-59`). A repo-wide search (2026-08-24) found **no
calibration receipt for that 1% anywhere** — the only calibration artifact
calibrates the IV solver (`options_researcher/iv_solver_calibration.py`,
`reports/iv_solver_calibration/*`).

**Honesty statement (binding; goes in the report in substance):** with no
execution records on disk (a guardrail-enforced absence), the 1% haircut
**cannot be calibrated** against realized fills, and comparing it to quoted
spreads is circular — the model already charges each contract's own
half-spread, so "half-spread + 1%" sits at or above it by construction
(rev-1 review finding 3, measured). What the cached bytes CAN answer,
non-circularly, is what this study measures:

1. **Decomposition** — how much of the model's total assumed adversity comes
   from half-spread vs. the 1% haircut vs. cent rounding, per bucket. This
   *describes the model*; it calibrates nothing, and is labeled so.
2. **Absolute overnight mid drift** — under the registered `D_PLUS_1_CLOSE`
   convention (`config.py:241`), a spread chosen at session D fills at
   session D+1's quotes. The session-over-session move of the same
   contract's mid is an **independent** quantity (yesterday-to-today mid
   change vs. today's spread), so placing the haircut inside its measured
   distribution is a legitimate, non-circular scale comparison.
   **"Absolute", not "adverse" (round-2 finding R2):** a bare chain carries
   no trade direction; review-measured, 45.1% of |Δmid| moves on the
   08-19→08-20 admitted set were *favorable* (5,216 up / 6,204 down / 151
   flat of n=11,571). Directional adversity would require a declared
   position side and is out of scope; the report states this and prints the
   up/down split beside every drift table.
3. **Two-leg net-credit drift (Strategy-A analogue)** — the seq-21 hybrid
   cancel/resize convention (`ledger/experiments.jsonl:22`;
   `config.A_ENTRY_CREDIT_TOLERANCE`, `config.py:244`) governs **future
   Strategy A put-credit-spread backtests only** and cancels when the D+1
   executable credit is more than the tolerance **below** signal credit
   (one-sided). Round-2 finding R4 measured that single-leg |Δmid| overstates
   two-leg net-credit drift ~4.5× at the median ($0.45 vs $0.10), so any
   tolerance comparison must be computed on constructed two-leg spreads,
   one-sided, and labeled an analogue — see Measurement 3.
4. **Touch depth (Tier-2 only, context)** — `bid_size`/`ask_size` on
   admitted contracts: is a 1-lot at the quoted touch plausible? Labeled
   Inference (quoted size is not fill evidence).

Closes the WS-1 / Candidate-A-narrow finding of the 2026-08-24 plan, as
re-scoped by two review rounds.

## Hash-identity consequence of landing this brief (round-1 finding 2)

Adding `tools/fill_haircut_calibration.py` changes `diagnostic_source_hash`
(`research/hashing.py:132` — `DIAGNOSTIC_SOURCE_PATHS_V2` includes `tools`).
**All statistics helpers live inside `tools/` — an `analysis/` sibling is
forbidden** (`analysis` is inside `SOURCE_HASH_PATHS`,
`research/hashing.py:17-26`). No `config.py` constants are added by this
brief (study parameters live in the tool and its receipt), so `config_hash`
is untouched. The merge must land outside the 07:10–15:45 ET operational
window with an immediate ops sync and a fresh source-health → data-gate
cycle after; the PR body must state that pre-existing sealed receipts will
no longer re-verify at the new hash (expected, not a defect). Fail-closed
consumers that refuse on identity mismatch:
`options_researcher/h7_watch.py:196-199`, `h7_data_gate.py:748`,
`h7_exit_session.py:247,267`, `tools/h7_data_audit.py:668`,
`research/diagnostics.py:156`.

## Scope

**IN:** one new read-only CLI `tools/fill_haircut_calibration.py` (all
helpers in `tools/` — see hash section); a dated report
`reports/fill_calibration/2026-08-24-fill-adversity-context.md` plus a JSON
receipt beside it; tests.

**OUT (binding):**
- **No change to `config.py`, `strategies/`, `metrics.py`, or any scoring
  path.** The frozen fill model is untouched; proposing a new frozen value is
  an owner amendment decision outside this brief.
- **No re-scoring of any registered result under an alternative haircut**
  (parent plan §10 item 2 stop condition).
- Quarantined chains_v2 sessions excluded ALWAYS — consume
  `data/v2_partition_quarantine.json` (Repo-verified: AMZN/AVGO/AMD
  2025-11-24, crossed markets). The Tier-2 audit warning profile at
  `.cache/chains_v2/od1-2026-08-01/_meta/full_audit.json` (Repo-verified,
  6.1 MB) must also be consumed: the receipt records per-session warning
  counts for every session used (round-1 finding 11 / parent plan §10
  item 5).
- No ledger/facts writes, no registration, no authority flips, no live-order
  paths, no paper-book access, no network (OD-4), no `.cache` writes, no
  merge/rebase of `codex/od1-v2-current`. No import of `research.experiments`
  anywhere in the tool — the 0/3 reveal budget is structurally untouched.
- Vocabulary discipline (`.cursorrules`): "consistent with" / "larger than" /
  "smaller than" only; "proven", "confirmed", "validated", "correct" are
  prohibited in deliverables and tests grep-assert their absence.
- Every table carries its max as-of session; Tier 1 and Tier 2 are never
  pooled into one table.

## Work packages

**WP-A — Tiered loader with fail-closed gating.**
- **Tier 1 (default, ungated):** `.cache/schwab_chains/*.parquet`
  (Repo-verified schema: legacy columns + `contract_symbol, multiplier,
  non_standard, mini, timestamp, trade_timestamp`; sessions 2026-08-14,
  08-19, 08-20 at audit time, growing daily; review-measured median quote
  age at capture 0.4 minutes — clean).
- **Tier 2 (gated):** `.cache/chains_v2/od1-2026-08-01/SYMBOL_DATE.parquet`
  (legacy columns + `timestamp, bid_size, bid_condition, ask_size,
  ask_condition, iv_error, underlying_timestamp, underlying_price,
  thetadata_client_version`; 18 symbols, 2025-07-25→2026-07-31). Loads ONLY
  behind `--allow-parked-chains-v2`; the refusal message cites the parked
  status and the 2026-08-24 owner ruling. **Prove both directions with
  tests.**
- **Tier-2 staleness filter (mandatory; round-1 finding 7, measured):** on
  the 2026-07-31 admitted subset, 28% of rows carry a midnight timestamp
  (never quoted that session) and 55% were last quoted before 15:00 ET.
  Pre-declared filter: keep only rows whose `timestamp` falls on the row's
  session date between 09:30 and 16:15 ET; count and report drops per
  session in the receipt. Round-2 finding R11 measured the typical
  admitted-row loss at ~25% (mean 25.3%, max 33.5% over 25 sampled
  sessions) — the executor should treat a session far outside that family
  as suspect. A session losing >50% of admitted rows is excluded from drift
  pairs and listed; R11 verified this rule fires on 0 of 25 current
  sessions — it is a safety net expected never to trigger, not a live
  filter.
- Basic validity (both tiers): drop rows with bid < 0, ask ≤ 0, or
  ask < bid; count drops in the receipt.
- Admission: `data.chain_policy.passes_liquidity`
  (`data/chain_policy.py:48-57`); the vectorized equivalent is
  `data/recent_topup.py:469-480` `_liquid_mask` (same predicate; use it for
  frame-level work).
- Underlying spot: Tier 2 rows carry `underlying_price` (preferred). Tier 1
  uses **raw** closes via `data.underlying_closes.load_closes(symbol, start,
  end, allow_oos=True)` — raw is correct for strike/spot math
  (`data/underlying_closes.py:48-52`); do NOT use `load_closes_adjusted`
  (Tier 2 spans a year; adjusted closes would corrupt moneyness across any
  split boundary). Binding note (round-1 finding 4): `allow_oos=True` is the
  closes cache's soft in-sample gate (`data/underlying_closes.py:44-55`
  raises `OOSDataTouchError` past 2022-12-31 without it); it is NOT the
  ledger reveal path (`research/experiments.reveal_oos`) and charges nothing
  against the 0/3 reveal budget — no `reveal_oos` call occurs anywhere in
  this tool. Missing close → session excluded from moneyness tables,
  recorded, never interpolated.

**WP-B — Measurements (pure functions in the tool).**

*Bucketing (round-1 finding 8; round-2 R9/R10):* headline tables pool across
symbols — buckets are DTE band × |delta| band. Bands (closed, pre-declared —
no slice-shopping): DTE `{0–7, 8–30, 31–60, 61–120, 121+}`; |delta|
`{0–0.15, 0.15–0.35, 0.35–0.65, 0.65–1.0}` **plus an explicit `OUT_OF_BAND`
bucket** for |delta| > 1.0 or NaN (round-2 R9: 72 of 11,772 admitted 08-20
rows fall there; `options_researcher/quote_integrity.py:101-105` classifies
these `INVALID_GREEK`, so they are a data-quality signal — counted in the
receipt, never silently dropped). Per-symbol breakdowns appear only in an
appendix at DTE-band granularity. Floor: `--min-bucket-obs` default `200`
rows on pooled tables (LLM-proposed power heuristic, not owner-typed); below
it a bucket renders `INSUFFICIENT (n=…)`, never numbers. Round-2 R10
measured 19 of 20 pooled Tier-1 buckets already clear the floor; the one
shortfall (`DTE 0–7 × |delta| 0–0.15`, n=189) will flip above/below it as
captures accumulate — a bucket appearing or disappearing between runs is
expected behavior, not a defect.

*Measurement 1 — Model decomposition (describes the model; labeled so).*
For each admitted contract, the model's per-leg adversity has three
components (`strategies/base.py:12-19,59-97`; round-1 finding 19): the
half-spread, the 1% haircut, and cent rounding (ceil/floor to the cent;
review-measured median 0.014% of mid). Report each component's share of the
total, per pooled bucket, per tier.

*Measurement 2 — Absolute overnight mid drift (the headline; round-2 R2/R3
applied).* Pairs = **adjacent** trading sessions (exchange calendar via
`mcal.get_calendar("XNYS")` directly — do NOT import `data.cache_runner`,
which pulls grpc + the ThetaData adapter at module level; brief-21
prohibition). For every contract admitted at session D and present, fresh,
at D+1 (matched on expiration/strike/right): `Δmid = mid(D+1) − mid(D)`.

- **Headline table:** percentiles of `|Δmid|/mid(D)` (p50/p75/p90/p95/p99)
  per pooled bucket, per tier, with the up/down/flat split printed beside
  each table (R2). One sentence per tier places `SLIPPAGE_HAIRCUT` inside
  that percentile table (review-measured Tier-1 reference points: p50
  0.0201, p90 0.1086, p99 0.5299 — the haircut sits below the median
  absolute overnight drift).
- **Appendix only (round-2 R3 — these saturate and must not headline):**
  the exceedance fractions. Review-measured on the 08-19→08-20 admitted
  set: `|Δmid|/mid > SLIPPAGE_HAIRCUT` = 67.4%; `|Δmid| > $0.01` = 98.0% —
  the latter is an artifact of one tick on dollar-priced options, and the
  appendix must say so explicitly. No exceedance fraction may appear in the
  headline, summary, or PR description.
- **Survivorship disclosure (round-2 R12, mandatory):** the drift sample is
  "contracts admitted at D that were still quoted and fresh at D+1" —
  vanished contracts and staleness-filtered rows drop out. The receipt
  records the count dropped at each stage; the report carries one paragraph
  stating the bias direction is **not determined** (dropping never-quoted
  rows removes Δmid ≈ 0 and biases drift up; requiring D+1 presence keeps
  liquid survivors and biases down).

*Measurement 3 — Two-leg net-credit drift, Strategy-A analogue (round-2 R4
replaces rev 2's single-leg tolerance comparison).* Construct every
adjacent-strike put vertical with BOTH legs admitted at D (review verified
n=4,352 on current Tier-1 data). Compute the D→D+1 change in the spread's
net credit and report, per pooled bucket:
- percentiles of |Δ(net credit)|;
- the **one-sided adverse** fraction: `Δ(net credit) < −A_ENTRY_CREDIT_TOLERANCE`
  (`config.py:244`; reference the constant, restate no value) — the
  direction and threshold the seq-21 gate actually uses. Review-measured
  context for the PR: two-sided single-leg `>$0.01` reads 98.0% while
  spread-level is 90.9% two-sided and 53.3% adverse-only single-leg —
  median leg drift $0.45 vs median net-credit drift $0.10 (4.5×), which is
  why the single-leg version is banned from this measurement.
- **Mandatory caveat, verbatim in substance:** "seq-21's tolerance governs
  future Strategy A put-credit-spread backtests only
  (`ledger/experiments.jsonl:22`); the chains measured here are the H7
  story-name universe, which seq 21 excludes. This is an analogue
  computed on a stated spread construction, not a compliance measurement."

*Measurement 4 — Touch depth (Tier-2 only; labeled Inference).* On admitted,
staleness-filtered contracts: distributions of `bid_size`/`ask_size`,
fraction with size ≥ 1 at the touch on each side, size-weighted mean spread
fraction. Explicit label: quoted size is not fill evidence; this bounds
1-lot plausibility only.

*Success criterion (round-2 R5 — falsifiable, replaces rev 2's
"worthwhile if it reports"):* the study reaches a decision-relevant finding
either way:
- If, in ≥1 pooled bucket meeting the observation floor, the p50 of
  `|Δmid|/mid` differs from `SLIPPAGE_HAIRCUT` by more than **2×** (in
  either direction), the finding is that the haircut's magnitude is out of
  scale with overnight quote movement in that bucket — reported plainly as
  input to a possible future owner amendment.
- If every qualifying bucket's p50 sits within 2× of the haircut, the
  finding is that the constant is the right order of magnitude and **no
  follow-up is warranted** — a null result recorded as such.
(The 2× factor is an Assumption — LLM-proposed order-of-magnitude bound,
not owner-typed; recorded in the receipt. Review-measured Tier-1 p50 ≈
0.0201 vs haircut 0.01 suggests the first branch is live, but the study
runs on the full accumulated data, not the review's single pair.)

**WP-C — Report + receipt emission.**
- Markdown report at
  `reports/fill_calibration/2026-08-24-fill-adversity-context.md`: the
  honesty statement, headline pooled tables per tier per measurement (with
  the R2 up/down splits and R12 survivorship paragraph), appendices
  (including the saturated fractions with their saturation note), a "what
  this is not" paragraph (not fill evidence; not a recommendation; not
  applicable to any registered result), every table stamped with max as-of
  session and n, the owner-ruling provenance line for Tier 2, and the
  Tier-2 staleness/warning-profile disclosure.
- JSON receipt beside it via `research/receipts.py` (`make_receipt` /
  `write_immutable_receipt`). Receipt facts (line numbers per round-2 R7):
  receipts carry **no wall-clock field** (`make_receipt` docstring,
  `research/receipts.py:58`) — determinism unconditional; the hardcoded
  `"receipt_schema": "h7-receipt/v1"` (`:60`) and "H7"-worded error strings
  (`:86`, `:98`) are a known misnomer — payload carries `receipt_type:
  "fill_adversity_context"` and tests load with an expected-type check;
  `write_immutable_receipt` raises `FileExistsError` on non-identical
  rewrite (`:109`, `:137`), so re-runs after code changes embed a
  payload-hash prefix in the filename, and tests write to
  `TemporaryDirectory`.
- Receipt content: input inventory (file/session counts per tier, quarantine
  exclusions, per-stage staleness/validity/survivorship drop counts,
  warning-profile counts, excluded sessions, `OUT_OF_BAND` counts), full
  numeric tables, study parameters (bands, floor, 2× factor), git SHA.

**WP-D — Tests (offline, `unittest`, no network).**
1. Tier-2 gate: refuses without `--allow-parked-chains-v2`; loads with it
   (both directions).
2. Quarantine exclusion holds even WITH the flag.
3. Staleness filter: fixture rows on both sides of the 09:30/16:15 boundary
   and a midnight-timestamp row; >50%-loss session exclusion.
4. Drift math pinned on hand-computed fixture vectors, including the
   one-sided net-credit adverse fraction and a case where |Δmid| is large
   but Δ(net credit) is small (the R4 two-leg effect).
5. Decomposition shares sum to 1 within tolerance on fixtures.
6. Min-obs floor renders `INSUFFICIENT`, never numbers; `OUT_OF_BAND`
   rows land in their own counted bucket and never vanish (R9).
7. Prohibited-vocabulary grep on the generated report fixture; additionally
   assert no exceedance fraction appears outside the appendix section (R3).
8. Never-pooled: Tier-1 and Tier-2 rows cannot enter the same table.
9. Raw-not-adjusted closes: `load_closes` (raw) called,
   `load_closes_adjusted` not.
10. **Behavioral no-network test** (round-1 finding 9): sockets denied for a
    full CLI run over fixtures; zero-call mock assertions on
    `fetch_underlying_eod*`, `get_eod_chain`, `blind_cache_chain`.
11. No `research.experiments` import.
12. Missing-close session exclusion and per-stage drop counts visible in the
    receipt.

## Acceptance / verification

```
uv run python -m unittest discover -s tests
uv run ruff check .
uv run pyright
```

Exit codes define done. Then run the tool for real in both modes (Tier-1
only; Tier-1+2 with the flag) and attach both stdout summaries to the PR.
The generated report and receipt ARE committed (dated findings under
`reports/` per repo layout), but only after the suite is green; nothing else
from the runs is committed. The PR body states the hash-identity consequence
(section above). Whatever the success criterion's branch turns out to be —
out-of-scale or right-order-of-magnitude — the report states it plainly and
stops; any follow-up (owner amendment to the haircut, or none) is explicitly
not this brief's job. Merge timing stays with the owner.
