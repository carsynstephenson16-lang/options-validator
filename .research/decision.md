# Phase 2 — Decision gate: intraday volume periodicity and alternatives

- **Decision date:** 2026-07-25 (research fan-out ran 2026-07-24; that is the
  research cutoff for all web evidence).
- **Decided by:** the parent session, independently, after reading the Phase 0
  baseline and all four Phase 1 files in full (`00_baseline.md`, `01_periodicity.md`,
  `02_licensing.md`, `03_strategy_candidates.md`, `04_repo_architecture.md`)
  plus parent-run spot-checks of the load-bearing repo claims (greps of
  `config.py`, `options_researcher/attractiveness.py`,
  `options_researcher/features.py`; direct read of
  `data/thetadata_adapter.py:1-60`; direct read of
  `reports/live_probe/2026-07-24.json`).
- **Candidates gated:** (A) the anchor, C1 — intraday volume periodicity /
  relative volume vs. time-of-day; (B) the strategy file's lead, C2 — options
  open-interest change / unusual OI build-up badge. The runner-up C4 (IV skew
  steepness) is not gated here; it goes to the ideas parking lot per the
  strategy file's selection.

---

## OVERALL OUTCOME: `RESEARCH-VALID, IMPLEMENTATION-REJECTED`

- **C1 (anchor): implementation REJECTED** — fails mandatory gates 1, 5, 6,
  and 9. The economic hypothesis itself is real and well-sourced (U-shape and
  spectral-periodicity literature), so the research is preserved and the
  candidate is parked, exactly the outcome the task's own data-reality-check
  anticipated as valid and successful.
- **C2 (lead): a genuinely stronger candidate — gates 1–8 PASS with evidence,
  but gate 9 FAILS for direct implementation in this session.** The
  proportionate, repo-governed path is an RQ2-style brief (written, see
  `.research/05_lead_candidate_brief.md`) whose frozen numbers the owner
  types/ratifies and Codex implements, joining the five already-committed
  RQ2 badges rather than jumping their queue.
- **No production strategy code was written. No placeholder code, no unused
  abstractions.** Per the workflow, a non-approval outcome is a successful
  completion, and per this repo's doctrine, "no implementation warranted yet"
  is a finding, not a failure.

Scope-guard sentence (required by `.cursorrules`): a new scanner badge is
context for the live H5/H6/H7 books' daily operation, the same class of
owner-sanctioned scanner-enrichment work as the committed RQ2 briefs — but it
does not itself move a hypothesis to verdict, which is precisely why it
belongs in the owner-gated RQ2 queue and not in this session's hands.

---

## Gate-by-gate results — C1, intraday volume periodicity (anchor)

### Gate 1 — Required inputs available free for live use: **FAIL**

- **Evidence.** The signal needs continuous (minute-or-finer) equity
  share-volume, live through each session (`01_periodicity.md` §3–4).
  Repo-verified: the live stock endpoint is PERMISSION_DENIED on the current
  ThetaData plan ("FREE" stock tier) per the live probe receipt
  `reports/live_probe/2026-07-24.json` — a real error from ThetaData's own
  service, read directly by the parent. The licensing audit
  (`02_licensing.md`) then walked every plausible provider:
  - **QuantConnect** (the source platform of the researched idea): free
    minute data exists ONLY inside Cloud notebooks/backtests; local download
    requires a paid organization tier plus per-file QCC credits, under an
    internal-LEAN-use-only, no-redistribution, no-format-conversion license
    (Official-source, quantconnect.com docs, 2026-07-24); live deployment
    requires a paid tier plus a paid live node. Fails "free," "local," and
    "live" simultaneously.
  - **ThetaData:** live/minute stock volume starts at the paid VALUE stock
    tier (Official-source, docs.thetadata.us Subscriptions, 2026-07-24).
  - **Alpha Vantage free:** 25 requests/day and non-live default — cannot
    serve 15 names intraday.
  - **yfinance/Yahoo:** Yahoo ToS §2.4(ix)/(x) explicitly prohibit the
    automated access method — a clear published "no," not an ambiguity.
  - **Polygon/Massive free:** EOD-batch only; live costs $29–$199/mo.
  - **Alpaca Basic (IEX):** the one $0, real-time, terms-compatible feed —
    but IEX carries ~3–6% of consolidated US equity volume (IEX's own
    published statistics), a venue-skewed slice whose intraday *shape*
    representativeness is untested.
- **Verdict logic.** The task's data-reality-check instructs FAIL when the
  signal depends on paid data, a paid QuantConnect tier, cloud-only data,
  or **insufficient market coverage**. Every full-market path is paid or
  license-blocked; the only free path fails market coverage. FAIL on the
  gate's own terms, not on a technicality.
- **Confidence:** high. **Open questions:** exact ThetaData stock-tier price
  (ambiguous across fetches), Finnhub/Twelve Data disputes — none of which
  could flip the gate (both are rate-thin or unverified, and neither offers
  full consolidated coverage free).
- **Failure consequence:** no honest live implementation exists at $0; a
  "pass" here could only be manufactured by substituting delayed/EOD data or
  the untested IEX slice — the exact conversions the workflow bans.

### Gate 2 — Published terms permit intended use: **FAIL** (for the inputs that matter)

- **Evidence.** QuantConnect data: no-redistribution/no-conversion,
  internal-LEAN-only (Official-source). Yahoo: prohibited. The only
  terms-clean free source (Alpaca, personal non-commercial) is the source
  that fails coverage in gate 1. Terms and availability never pass on the
  same provider.
- **Confidence:** high. **Consequence:** any workaround would rest on either
  a license breach or an unverified representativeness assumption.

### Gate 3 — Signal calculation avoids look-ahead: **PASS (design-level)**

- **Evidence.** A causal construction is well-defined and documented
  (`01_periodicity.md` §2b, §7): strictly-trailing profile windows, never
  normalizing today against a window containing today, never dividing by the
  same day's final total, half-day/session-calendar handling, split-adjusted
  volume. QuantConnect's own RDV formula is the causal form.
- **Confidence:** high that a leak-free construction exists; the named leak
  modes are real and would need tests. This gate passing does not rescue the
  candidate — gates 1, 5, 6, 9 still fail.

### Gate 4 — Adds information beyond existing features: **PASS**

- **Evidence.** Parent-verified grep: no equity share-volume feature exists
  anywhere in the scanner (`config.py`'s only "volume" constant is
  `QM_VOL_DRYUP_RATIO`, a retired-QM-study parameter; `features.py` and
  `attractiveness.py` have none). Architecture map §4/§7 confirms nothing
  volume- or intraday-timing-based exists or is planned in the RQ2 briefs.
  Genuinely orthogonal — this is the candidate's one unambiguous strength.

### Gate 5 — Clear mechanism connects signal to options selection: **FAIL**

- **Evidence.** `01_periodicity.md` §8: no fetched source ties volume
  periodicity to option IV, skew, direction, or strike/expiry choice. The
  QuantConnect page's own use is a cross-sectional long-equity factor over
  the 100 most liquid names — not an options-selection mechanism, and its
  specific backtest numbers could not be independently corroborated. The one
  defensible link — execution timing (when in the session quotes are
  trustworthy) — cannot be exploited by a scanner that evaluates a handful
  of discrete snapshots per day.
- **Confidence:** high. **Consequence:** implementing anyway would bolt an
  equity-microstructure signal onto an options board with no stated causal
  bridge — decoration, not information.

### Gate 6 — Architecture supports a focused implementation: **FAIL**

- **Evidence.** Architecture map §1–3, §8: the entire feature layer is
  EOD-grain (one row per symbol-day), rebuilt once per daily ritual; the
  live lane is 5 discrete probe-gated snapshots with parity-derived spot and
  no equity feed. A periodicity signal would need a new continuous ingestion
  pipeline, a new intraday store, and a new operating cadence — a structural
  departure, not a focused addition.
- **Confidence:** high.

### Gate 7 — Data supports a meaningful evaluation: **PARTIAL (moot)**

- **Evidence.** Historical evaluation is possible in principle (free
  QuantConnect Cloud notebooks; Alpaca IEX minute history since 2016), but
  the evaluable datasets are not the deployable feed (cloud data is
  non-exportable; IEX is the venue slice from gate 1) — so an evaluation
  would test a signal the repo could not honestly run live. Recorded as
  partial; does not affect the outcome given gates 1/5/6/9.

### Gate 8 — Test plan distinguishes signal validity from code correctness: **PASS (in principle, moot)**

- **Evidence.** The repo's test discipline (causality property tests,
  offline unittest, DATA_BLOCKED fail-visible pattern) could cover code
  correctness; signal validity would need its own registered study. Moot
  given the other failures.

### Gate 9 — Implementation risk proportionate to expected value: **FAIL**

- **Evidence.** Costs: a new external data relationship, new pipeline, new
  cadence, new leak surface (gate 3's list), ongoing venue-representativeness
  doubt. Value: a signal with no established options-selection mechanism
  (gate 5) on a 15-name thematic board far from the 100-name liquid
  cross-section the source result was built on (`01_periodicity.md` §6).
  Disproportionate by a wide margin.

### C1 cheapest valid future path (recorded, not purchased or integrated)

1. **ThetaData stock VALUE tier upgrade** (paid; exact price unresolved this
   session — the audit could not cleanly separate stock from options tier
   pricing) would deliver 1-minute history from 2021 (15-min delayed) on the
   already-integrated provider; STANDARD adds real-time. This is the cheapest
   *coherent* path and it is not free — so the gate result stands until the
   owner chooses to spend.
2. Free-but-weaker alternative: a **once-daily descriptive daily-volume
   feature** (daily OHLCV volume is already cached in
   `.cache/underlying_ohlcv/` for the QM study — no new provider) — but that
   is a different, weaker hypothesis than the anchor and would need its own
   fresh justification; it is NOT approved by this document.
3. If intraday ever matters enough to test: an **IEX-vs-consolidated shape
   representativeness study** must precede any Alpaca-based build.

---

## Gate-by-gate results — C2, options OI-change badge (lead candidate)

### Gate 1 — Inputs free for live use: **PASS**

- Historical: `open_interest` is already a column in every cached chain
  (`data/thetadata_adapter.py::CHAIN_COLUMNS`, parent-verified), fetched via
  `option_history_open_interest` on the existing paid options subscription.
  Live: `option_snapshot_open_interest` returned `ok` with an
  `open_interest` column in the live probe receipt
  `reports/live_probe/2026-07-24.json` (parent-read primary evidence). Zero
  new data, zero new endpoints, zero new spend.
- **Confidence:** high. **Open question:** none material; the live endpoint
  denial risk the strategy file flagged is resolved by the probe receipt.

### Gate 2 — Terms permit use: **PASS**

- Same already-subscribed ThetaData options data the repo lawfully uses
  daily; personal/Individual-tier use consistent with a research-only,
  no-orders validator (Official-source terms quoted in `02_licensing.md` §2).
  Residual Assumption (disclosed): the ToS anti-automation boilerplate is
  read as targeting the website, not the paid API a subscriber queries by
  design.

### Gate 3 — No look-ahead: **PASS**

- The adapter's own documented design: OI comes from the ~06:30 ET OPRA
  report reflecting the PRIOR day's close, "already known during day D, so
  joining day-D OI is look-ahead-free" (`data/thetadata_adapter.py:14-17`,
  parent-read). A day-over-day delta of prior-known values is causal by
  construction; the "unusual vs. own history" normalization must use a
  strictly-trailing window with a truncation property test (the committed
  RQ2 Brief B1 pattern).

### Gate 4 — Adds information: **PASS**

- Parent-verified: `open_interest` appears in the scanner only as a static
  per-contract level inside `passes_liquidity()` at five call sites in
  `attractiveness.py` — never a change, flow, or history signal. No RQ2
  brief touches OI dynamics. New axis, zero code overlap.

### Gate 5 — Mechanism to options selection: **PASS (as display context; disclosed adaptation)**

- Per-strike, per-contract signal on exactly the cards the scanner renders;
  mechanism: new positioning accumulating at specific strikes as context for
  a seller/buyer already choosing among those strikes. The peer-reviewed
  base (Pan & Poteshman 2006; Johnson & So 2012) is about option *volume*,
  not OI — the OI variant is a mechanistically-adjacent adaptation, honestly
  scored 3/5 in `03_strategy_candidates.md` and disclosed as such. This
  clears the bar for a display-only context badge; it would NOT clear the
  bar for a verdict-bearing or rank-changing signal without its own
  registered study.

### Gate 6 — Architecture fit: **PASS**

- The smallest complete integration is already mapped and precedented
  (architecture map §15): a `features.py` column, a `grades` dict badge via
  the existing `grade()` helper, one `config.py` constant family, the
  `DATA_BLOCKED` pattern for gaps, a per-module test file. Mirrors the
  committed Brief B1 design exactly.

### Gate 7 — Data supports evaluation: **PASS**

- Years of cached per-strike, per-day OI for all 15 names sit in
  `.cache/chains/` (18k+ parquet files per the data-decisions record),
  fully offline — historical distributions of OI changes are computable
  without any network call.

### Gate 8 — Test plan separates validity from correctness: **PASS**

- Code correctness: formula tests, causal truncation test, missing-day and
  thin-OI handling, staleness (the existing `features_stale` machinery),
  interaction-with-ranking test (badge must not change Top-3 ordering —
  the RQ2 briefs' standing acceptance criterion). Signal validity: explicitly
  NOT claimed by the badge; any validity claim requires a separately
  pre-registered descriptive study. The brief states this separation.

### Gate 9 — Risk proportionate to value: **FAIL — for direct implementation in this session**

- **This is a governance failure, not a data or code failure, and it is
  binding.** The badge requires frozen numbers (lookback window, "unusual"
  percentile threshold, minimum-OI floor). This repo's standing owner
  directives (operating manual, 2026-07-16/22 amendments; division-of-labor
  directive 2026-07-22) are explicit: the owner types every frozen number;
  LLM-proposed numbers are labeled and tested, never frozen as-is; Codex
  implements from briefs; Claude writes docs and briefs. Five
  owner-reviewed RQ2 badges are already committed and waiting on exactly
  this ratification step. A sixth badge implemented directly here, with
  self-chosen thresholds, would (a) freeze LLM-asserted numbers — the thing
  the manual calls pre-registration theater — and (b) silently jump an
  owner-gated queue. Expected value (a display-only context badge) does not
  justify that integrity cost when a zero-cost compliant path exists: the
  brief in `.research/05_lead_candidate_brief.md`.
- **What would flip this gate:** owner ratification of the brief's numbers
  (typing them into the delegated-values flow), at which point
  implementation is a normal Codex task with the test plan above. Nothing
  about the data, licensing, mechanism, or architecture blocks it.

---

## Explicit anti-conversion checklist (workflow requirement)

No FAIL above was converted to PASS by: lowering data resolution without
retesting the hypothesis (the daily-volume idea is recorded as a *different,
unapproved* hypothesis, not a pass for C1); substituting historical for live
data; assuming undocumented API access (the live probe receipt is the
opposite — documented denial); ignoring licensing restrictions; treating
correlation as options-selection value; or writing code before the gate.

## Dispositions

| Candidate | Disposition |
|---|---|
| C1 — intraday volume periodicity | REJECTED for implementation; research preserved in `.research/01_periodicity.md`; parked in `ideas-parking-lot.md` with its failed dependency and cheapest future path |
| C2 — OI-change badge | Gates 1–8 pass; implementation deferred to the owner-gated RQ2 pipeline; ready-to-ratify brief at `.research/05_lead_candidate_brief.md`; parked pointer in `ideas-parking-lot.md` |
| C4 — IV skew steepness (runner-up) | Parked in `ideas-parking-lot.md` per `03_strategy_candidates.md` (strong mechanism; needs frozen strike/tenor convention + small-universe external-validity memo first) |
| C3, C5 | Not selected; scoring preserved in `03_strategy_candidates.md`; no parking-lot entry (C3's volume-true form additionally depends on an unverified `option_snapshot_trade` entitlement) |

---

## Post-verification addendum (2026-07-25)

The adversarial verifier (`.research/07_verification.md`) returned
**UPHELD-WITH-CORRECTIONS**: zero critical, zero major, three minor findings.
Dispositions:

- **MINOR-1 (file-count miscount in this document):** fixed in place above
  ("the Phase 0 baseline and all four Phase 1 files").
- **MINOR-2 (14-vs-15 universe wording drift across research files):** the
  authoritative count is **15 names** (`config.ATTRACTIVENESS_UNIVERSE`; the
  task brief's own list of 14 omitted USAR). `02_licensing.md` §0 discloses
  and explains this, and every provider cap was evaluated against 15, the
  conservative number. The subagent-authored research files are left as
  written; this addendum is the correction of record. No gate outcome
  depends on the difference.
- **MINOR-3 (licensing enumeration gap):** the audit did not individually
  enumerate Databento, Cboe One, or Nasdaq Basic. The verifier checked all
  three independently (2026-07-25): Databento is a one-time $125 credit then
  a paid subscription, Cboe One is paid and partial-venue, Nasdaq Basic is
  paid single-SIP — none is a free full-consolidated live feed, so Gate 1's
  FAIL for C1 stands unchanged.

The verifier also independently re-fetched the three load-bearing licensing
claims (QuantConnect internal-LEAN-only license; ThetaData stock tiers
FREE=EOD-only; Alpaca Basic=IEX-only), re-read every cited repo artifact
including the live probe receipt, git-verified that no `.py`/config/test file
was touched, and ran a deliberate (failed) hunt for a missed free full-market
live volume source. The overall outcome `RESEARCH-VALID,
IMPLEMENTATION-REJECTED` and the C2-to-brief routing are unchanged.
