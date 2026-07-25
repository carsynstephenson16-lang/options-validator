# Candidate scanner signal: Intraday volume periodicity

**Research cutoff / access date:** 2026-07-24
**Scope:** research-only note evaluating "intraday volume periodicity" as a candidate
input to the options-attractiveness scanner. No code written, no config changed,
no strategy proposed. Evidence labels used throughout: **Official-source**,
**Repo-verified**, **Inference**, **Assumption** (per CLAUDE.md claim discipline).
Vocabulary discipline observed: no "proven/confirmed/works/edge found" language.

---

## 1. Hypothesis

**Core, long-established empirical fact:** trading volume in individual equities
is not flat across the trading day. It traces a "U-shape" — heavy at the open,
heavy again into the close, and thin through the middle of the session.
**Official-source:** Wood, McInish & Ord (1985), *"An Investigation of
Transactions Data for NYSE Stocks,"* *Journal of Finance* 40(3), 723–739 —
using NYSE transactions data from 1971–72 and 1982, they document unusually
high returns AND high return variability at the open and close relative to
mid-day, the original empirical U-shape finding (see source log for exact
excerpt).

**Theoretical explanation:** Admati & Pfleiderer (1988), *"A Theory of Intraday
Patterns: Volume and Price Variability,"* *Review of Financial Studies* 1(1),
3–40, model WHY the U-shape arises: discretionary ("liquidity") traders who are
free to choose when to trade strategically cluster their trading together in
time, because clustering lets them hide behind each other and reduces the
adverse-selection cost of trading against better-informed counterparties.
Informed traders then also concentrate their trading in those same
high-liquidity windows to camouflage their orders. The result is an
endogenous, self-reinforcing concentration of volume (and of return
variability, since informed trading moves prices) at particular times of day —
canonically the open and close. **Official-source** (per WebSearch-derived
abstract/summary; original article not directly fetched in full — see source
log confidence note).

**Modern extension (the QuantConnect treatment this task asked about):** a more
recent academic strand looks for periodicity at much higher frequency than the
coarse open/mid-day/close U-shape — recurring volume spikes every N minutes or
seconds, attributed to systematic/algorithmic execution schedules (VWAP/TWAP
slicing, scheduled rebalancing, etc.) rather than the classical liquidity/
informed-trader story alone. **Official-source:** Wu, Zhang & Dai,
*"Spectral Volume Models: Universal High-Frequency Periodicities in Intraday
Trading Activities,"* *Management Science* (2024/2025 publication cycle;
SSRN working paper id 4230610) — they use Fourier/spectral analysis to show
persistent, high-frequency periodicities in both U.S. and Chinese equity
volume, attributed to "trading algorithms with repeated and regular trading
instructions," and report that these periodicities help forecast intraday
volume and improve VWAP execution quality (WebFetch-derived abstract
paraphrase; direct SSRN PDF fetch was blocked — HTTP 403 — see source log).

**QuantConnect's stated economic hypothesis** (from the target page, as
summarized by WebFetch — see Section 10 for confidence caveats): *"Periodic
trading carries more information content, so investors face greater adverse
selection and demand a higher return to hold the most periodic stocks."* This
extends the Admati–Pfleiderer adverse-selection logic from "time of day" to
"how mechanically periodic is this stock's trading" as a cross-sectional,
per-name characteristic, and proposes it as a priced risk factor (ranking the
most liquid US names by periodicity strength and going long the top quintile).
**Inference:** this is a step beyond both cited academic papers — neither Wood/
McInish/Ord nor Admati/Pfleiderer, nor (per the abstract available to me) Wu/
Zhang/Dai, claim a cross-sectional RETURN premium for periodicity strength;
that specific claim traces only to the QuantConnect post's own backtest, which
is a single historical demonstration, not an academic result.

**Practical uses this motivates:**
(a) a **relative-volume (RVOL)** signal — is right-now participation unusually
high or low for this time of day — used as an execution-timing / liquidity-
confirmation tool; and
(b) a **periodicity-strength** signal — how much of a name's volume is
explained by a small number of recurring cycles — used as a cross-sectional
ranking characteristic (the QuantConnect factor) or, more speculatively, as a
proxy for how much "algorithmic fingerprint" / adverse-selection risk a name
carries.

---

## 2. Mathematical formulas

### 2a. Classical diurnal volume-profile estimation (seasonal decomposition)

The standard practitioner/academic method to estimate a stock's typical
intraday volume "shape" divides the session into B fixed clock-time buckets
(e.g., 5- or 30-minute bars) and averages *normalized* volume in each bucket
across a trailing window of N days:

```
V̄(b) = (1/N) · Σ_{d=1}^{N}  v_d(b) / VolDay_d
```

where `v_d(b)` is the volume traded in bucket `b` on day `d`, and `VolDay_d`
is that day's total session volume (normalizing removes day-to-day volume-
level differences so the SHAPE, not the level, is averaged). `V̄(b)` across
`b = 1..B` is the diurnal profile (the U-shape curve). **Inference/generic
methodological convention** — this is the standard construction described
across the academic literature on dynamic intraday volume curves; I did not
verify a single canonical formula reference for this exact normalization inside
any one fetched source, so label it as standard-practice inference rather than
a direct quote.

### 2b. Relative-volume (RVOL) normalization — Official-source, directly fetched

QuantConnect's documented **Relative Daily Volume** indicator (fetched
successfully, not JS-blocked):

> "Current volume from open to current time of day / Average over the past x
> days from open to current time of day"

i.e.

```
RVOL_t = CumVol(open → t, today) / [ (1/N) · Σ_{d=1}^{N} CumVol(open → t, day d) ]
```

`RVOL_t > 1` = above-typical cumulative participation for that time of day;
`< 1` = below-typical. The documentation's own code example instantiates the
lookback as `RDV(symbol, 2)` — a 2-day lookback in the shown demo (almost
certainly a toy/illustrative default, not a recommended production value — see
Section 5 on estimation noise). **Official-source:**
`quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators/relative-daily-volume`.

### 2c. Periodicity-strength / spectral decomposition

The QuantConnect target page (per WebFetch, cross-checked twice with
consistent wording — see Section 10) defines two derived fields but, per my
attempts, does **not** show the underlying computation on the page itself:

- `volume_variance_explained` — "the fraction of de-trended intraday volume
  variance explained by the strongest periodic terms."
- `volume_dominant_period_seconds` — the time interval at which the volume
  pattern repeats.

The academic source it cites (Wu/Zhang/Dai 2025) uses Fourier/periodogram
analysis for exactly this construction. The standard periodogram estimator
that would produce these two fields (general spectral-analysis convention,
**Inference** — not verbatim from either fetched source, since neither page
showed the literal periodogram formula to me):

```
I(ω_j) = (1/N) · | Σ_{t=0}^{N-1} x_t · e^(-i·ω_j·t) |²,     ω_j = 2πj/N
```

where `x_t` is the de-trended/de-meaned high-frequency volume series over one
session (or pooled across sessions) and `N` is the number of intraday samples.
Then:

```
dominant frequency  j* = argmax_j I(ω_j)
volume_dominant_period_seconds = (sampling interval in seconds) / j*   [equivalently 1/f*]
volume_variance_explained = I(ω_j*)  /  Σ_j I(ω_j)     (or sum over the top-k harmonics)
```

This matches the qualitative description WebFetch returned for the Management
Science abstract: "a periodogram-based approach reveals consistent
high-frequency cycles... dominant frequency components explain a substantial
portion of intraday volume variation."

### 2d. QuantConnect strategy-level formulas (directly and consistently fetched)

Two portfolio-construction formulas were returned identically across two
independent WebFetch calls to the same URL (a reasonable internal-consistency
check given WebFetch is AI-summarized, not verbatim HTML — see Section 10):

```
r_i = 1 + e_i / max_j(e_j)      # raw weight from execution intensity e_i
w_i = r_i / Σ_j(r_j)            # normalized long-only portfolio weight
```

These are **position-sizing** formulas (weighting the top-quintile periodicity
names by execution-intensity score), not the periodicity-estimation formulas
themselves.

---

## 3. Required inputs and sampling frequency

- **Bar resolution:** minute bars at minimum for RVOL-style relative-volume
  work; the "seconds" unit on `volume_dominant_period_seconds` implies the
  underlying academic/QuantConnect treatment actually works at tick or
  sub-minute resolution to resolve short periodicities. A minute-bar-only feed
  would only resolve periodicities of several minutes or longer.
- **Fields:** timestamp (session-local clock time, not just date), share
  volume per bar; ideally trade count and/or VWAP per bar for cross-checks.
  Raw (not back-adjusted) share volume is the normal convention, with explicit
  split-ratio handling (see Section 7).
- **Lookback length:** enough trading days on the SAME intraday grid to
  average out single-day noise. QuantConnect's own RDV doc example uses N=2
  (illustrative only); broader academic dynamic-volume-curve work commonly
  uses 20–60 trading days. No canonical "correct" N was found in any fetched
  source — treat as a design choice with a stated noise/staleness tradeoff
  (Section 5).
- **Calendar metadata:** a regular-vs-early-close session flag and a holiday
  calendar are required inputs alongside the raw bars, or half-days corrupt a
  fixed-clock-time bucket grid (Section 5).
- **Universe:** the QuantConnect page's own construction ranks "the 100 most
  liquid US equities" (per WebFetch) — i.e., it is a cross-sectional,
  liquid-large-cap design, not calibrated to this repo's much smaller,
  thematically concentrated universe (Section 6).

---

## 4. Live-data requirements

For a LIVE scanner to compute this signal daily without look-ahead, it would need:

- **Continuous or near-continuous intraday equity volume**, updated frequently
  enough that the running `CumVol(open → t, today)` numerator reflects only
  what has actually traded up to "now" — a once-daily EOD batch feed cannot
  support the live/real-time use case (RVOL as an execution-timing signal),
  though it could support a coarser, once-daily DESCRIPTIVE read computed
  after the close (comparing today's realized shape to history), which is a
  materially weaker and different use case.
- **Low enough latency** that "now" is meaningfully "now" — a feed delayed by
  many minutes defeats the purpose of a time-of-day-specific timing signal.
- **Full-session coverage** every trading day (not just periodic snapshots),
  because the profile denominator needs same-clock-time history and any
  live-side numerator needs a genuinely running cumulative total.

**Repo-specific gap (Repo-verified via `.research/00_baseline.md`, which itself
flags the underlying entitlement fact as not yet independently verified by a
licensing researcher):** the live scanner in this repo currently runs on 5
discrete ThetaData snapshots per day and, per that file, is **not entitled to
stock/greeks endpoints** — live spot is derived indirectly from options parity,
not a direct equity feed. Two consequences follow directly from that
documented state:

1. There is no live minute-bar (or finer) **equity share-volume** feed in the
   project's current entitlement — the parity-derived spot doesn't carry
   volume at all.
2. 5 snapshots/day is far too sparse to build or update an intraday
   volume-periodicity profile, which needs a continuous or near-continuous
   series through the session.

**Inference:** on the evidence in the repo's own baseline note, this signal
would require a **new** data entitlement (an equity trade/quote feed with
volume, not just the existing options-chain access) before it could run live
at all — it is not a signal that can be built from data the scanner already
has rights to, unlike e.g. `rv21` or the options-chain-derived IV fields.

**No-look-ahead constraint specific to a live implementation:** the historical
baseline profile used to normalize "today" must be built only from strictly
prior sessions (a rolling/expanding trailing window, refreshed after each
session closes, never re-estimated in a way that folds in the current or a
future session — see Section 7 for the general leakage failure mode).

---

## 5. Statistical weaknesses

- **Estimation noise from short lookbacks:** a per-bucket average over few
  days (e.g., the doc example's N=2) has high sampling variance; single
  unusual days dominate the "typical" profile.
- **Non-stationarity:** the diurnal shape drifts over time (changing market
  structure, growth of the closing auction, changing algo prevalence), so a
  profile estimated even a year ago may misdescribe current behavior.
- **Holiday / half-day effects:** early-close sessions (e.g., day-after-
  Thanksgiving 1pm ET close) compress the normal closing-volume surge earlier
  in clock time and shrink total session volume; pooling these into a
  fixed-clock-time profile without a flag either injects a spurious pattern
  into a "normal" bucket or produces a nonsensical ratio for the whole
  half-day unless explicitly excluded or separately modeled.
- **Earnings-day / scheduled-event distortion:** an issuer's own earnings day
  (or macro events — FOMC, CPI, monthly opex) produces an atypical volume
  level and shape that can swamp the "typical" seasonal/spectral profile if
  not flagged or excluded — the same general class of contamination this
  repo's own earnings-cycle machinery already treats carefully for OTHER
  signals (Section 9).
- **Single-backtest inference risk:** the QuantConnect page's headline
  performance figures (per WebFetch: ~0.792 vs. ~0.406 Sharpe over one
  backtest window) describe one historical path for one specific cross-
  sectional, 100-name, long-only factor construction. Per this repo's
  vocabulary discipline, that is at most "not yet rejected" for THAT
  construction — it says nothing about a narrower, single-name or
  options-specific application, and I could not independently verify the
  exact backtest numbers beyond WebFetch's AI-generated summary (Section 10).
- **Periodogram-specific noise:** classical spectral-analysis theory says a
  raw periodogram estimate from one finite sample is itself a noisy (not
  consistent) estimator of the true spectral density at any single frequency;
  meaningful use requires averaging/smoothing across many sessions or
  frequency bins, which again ties back to the lookback-length tradeoff above.
  **Inference** (general statistical fact about periodogram estimators, not
  sourced from a specific fetched document here).

---

## 6. Market-regime sensitivity

- Volume level and shape both shift across regimes: high-stress periods (e.g.
  2020 COVID, 2022 drawdown) typically show elevated and reshaped volume
  (heavier open-driven or panic-selling clusters) relative to calm regimes; a
  profile fit in one regime can misdescribe another. **Inference**, consistent
  with the general microstructure literature but not independently re-derived
  here.
- The Admati–Pfleiderer mechanism itself assumes discretionary liquidity
  traders are FREE to time their trades; regimes with forced flows (margin
  calls, redemptions, circuit-breaker halts) break that free-timing
  assumption, so the theoretical basis for the U-shape is itself
  regime-conditional. **Inference.**
- The higher-frequency "algorithmic fingerprint" story (Wu/Zhang/Dai,
  QuantConnect) depends on the prevalence and consistency of systematic
  execution schedules, which can itself change with market-structure
  regulation, exchange fee-schedule changes, or shifts in the investor base
  (more/less passive indexing, different VWAP-algo adoption) — the
  "generating mechanism" is not a stable physical constant across time.
  **Inference.**
- This repo's own universe (VST/CEG/MSFT/AMZN core plus the H7 story-name
  watchlist such as PLTR, NVDA, IREN, USAR, SMCI, etc. — **Repo-verified**,
  `config.py`) is thematically concentrated and mostly not the "100 most
  liquid US equities" cross-section the QuantConnect factor is built on;
  whatever cross-sectional statistical properties the QC factor exhibits need
  not transfer to this narrower, higher-beta, single-thesis universe.

---

## 7. Look-ahead and leakage risks

- **The canonical naive-implementation leak:** estimating the historical
  baseline profile (the RVOL denominator, or the seasonal/spectral profile)
  using a window that INCLUDES today's own data. If today is folded into the
  N-day average used to normalize today's own reading, an unusually
  high-volume day partially normalizes against itself — and if a backtest
  ever estimates the profile ONCE over the WHOLE sample window (rather than a
  strictly-trailing rolling/expanding window), it literally uses future
  sessions to grade past ones. This is exactly the failure mode named in the
  task prompt and is the single most important leakage risk for this signal
  class.
- **Full-day-total leakage:** computing a bucket ratio by dividing an
  intraday cumulative reading by that SAME day's eventual close-of-business
  total volume leaks the end-of-day outcome into every earlier intraday
  ratio (e.g., a 10:00am reading would already "know" how much volume the
  whole day eventually did). The correct construction — and the one the
  QuantConnect RDV formula actually uses (Section 2b) — compares
  cumulative-to-time-`t` volume against OTHER days' cumulative-to-the-
  same-time-`t` volume, never against the current day's own final total.
- **Backtest/live mismatch:** this repo's own guardrail (`.cursorrules`: "at
  each decision timestamp use only data available at or before it") requires
  a strictly-trailing rolling estimation window, re-fit only after each
  session closes — a periodicity/RVOL feature computed any other way in a
  backtest would silently violate the repo's no-look-ahead rule.
- **Calendar/half-day leakage:** if a live system's holiday/early-close
  calendar isn't known in advance for a schedule change (rare but possible),
  the day's clock-time buckets could be misjudged against the wrong
  reference profile — an operational rather than a strict data leak, but
  still corrupts the ratio.
- **Corporate-action leakage:** splits or spin-offs occurring mid-lookback
  change raw share volume by the split ratio with no change in true
  participation; an unadjusted volume series can manufacture a spurious
  "volume regime break" that a naive detector could misread as a genuine
  periodicity signal unless volume is split-adjusted. This mirrors a caution
  this repo already applies elsewhere: `config.py`'s `STUDY_ERA_START` note
  on AMZN explicitly keeps the underlying close series "deliberately RAW
  (strike-aligned)" because the 2022-06 20:1 split would otherwise read as a
  spurious cycle (**Repo-verified**, `config.py` lines ~62–68) — the same
  class of split-handling discipline would need to apply to any volume series
  used for this signal.

---

## 8. Expected relationship to options liquidity, volatility, direction, and timing

- **Liquidity (Inference, not measured in this repo):** equity RVOL is a
  plausible concurrent proxy for when option market-maker inventory and
  quoting activity is deepest — high equity-participation windows (open,
  close) often coincide with tighter option quotes on an intraday basis.
  However, this repo's existing liquidity gates (`MIN_OPEN_INTEREST`,
  `MAX_SPREAD_PCT` in `config.py`, enforced via `passes_liquidity()` in
  `options_researcher/attractiveness.py`) are evaluated against a single
  daily chain snapshot, not intraday-timed — so a volume-periodicity signal
  would be a genuinely NEW kind of gate (WHEN in the session to check/enter),
  not a replacement for the existing static per-contract checks.
- **Volatility (Inference):** intraday volume and intraday return variability
  are documented as jointly U-shaped (Wood/McInish/Ord; Admati/Pfleiderer),
  and names with stronger periodicity may carry more informed/algorithmic
  flow, which the theory ties to adverse selection. Whether that translates
  into a measurable relationship with OPTION implied volatility or with this
  repo's own `rv21` / IV-rank fields is **not established by anything I
  fetched** — it would require a dedicated repo-side study, not an assumption
  carried over from the equity-volume literature.
- **Direction (Assumption — unsupported by anything fetched):** nothing in any
  source reviewed here ties volume periodicity to the SIGN of the next price
  move. The QuantConnect factor is a cross-sectional, long-only tilt toward
  periodicity STRENGTH across many names, not a directional timing signal for
  any one name. Using it as a directional input to an options strategy would
  be a repo-original extension with no external evidentiary support.
- **Timing (the most defensible mechanistic link, still Inference):** the
  strongest tie to this repo's existing guardrails is to EXECUTION TIMING —
  using intraday RVOL to decide WHEN inside a session to check quotes or
  attempt an entry, on the logic that low-participation windows are more
  likely to have stale or artificially wide posted quotes, which interacts
  directly with this repo's "fill at mid or worse, plus a slippage haircut"
  cost-model guardrail (`.cursorrules`).

---

## 9. Overlap with existing scanner signals

Read directly: `/Users/carsynstephenson/options-validator/config.py` and
`/Users/carsynstephenson/options-validator/options_researcher/attractiveness.py`
(read-only, per task scope). **Repo-verified** findings:

- **No equity share-volume feature currently exists.** `config.py`'s only
  liquidity-related constants are `MIN_OPEN_INTEREST` and `MAX_SPREAD_PCT`
  (checked via `passes_liquidity()`, imported from `data.thetadata_adapter`
  in `attractiveness.py`) — both are **option-contract** fields (the
  option's own open interest and bid-ask spread), not underlying-equity share
  volume. There is no `RVOL`, no volume-profile, and no periodicity constant
  anywhere in `config.py`.
- **Volatility-side overlap (Inference, conceptual not code-level):** the
  closest related existing family is `rv21` (trailing 21-session realized
  vol), `iv_rank` and its thresholds (`H5_IVR_SELL_GREEN`, `H5_IVR_BUY_GREEN`,
  `H5_IVR_BUY_RED`), and the VRP proxy `H5_VRP_SELL_GREEN` /
  `iv_minus_rv` (built in `_vrp_seller_grade()` in `attractiveness.py`).
  Because Admati–Pfleiderer's mechanism links volume clustering and
  return-variability clustering as the SAME underlying microstructure
  phenomenon, a periodicity signal could be read as a third, partially
  overlapping lens on something `rv21`/IV-rank already proxy for, rather than
  a fully independent axis — but this is an inference about economic
  mechanism, not a code-level duplication (no shared inputs or formulas
  exist today).
- **Momentum/technical side — no overlap.** The dashboard-only technicals in
  `config.py` (`TECH_SMA_WINDOWS`, `TECH_BREAKOUT_LOOKBACK`, `TECH_MOM_1M`,
  `TECH_MOM_3M`, `TECH_52W_LOOKBACK`) are price-based, not volume-based. A
  periodicity signal would be a genuinely new input dimension alongside
  these, not a duplicate of any of them.
- **Earnings/event-handling pattern is directly reusable, though the
  machinery itself is not.** `attractiveness.py`'s `ladder_cards()` /
  `earnings_in_cycle` / `earnings_unknown` logic (backed by
  `config.EARNINGS_COVERAGE_DAYS`) already implements a tested, fail-visible
  pattern: certify "clean" only when calendar coverage genuinely supports it,
  else badge `UNKNOWN` rather than a falsely reassuring `GREEN`. Section 5's
  earnings-day-distortion weakness for a periodicity signal would need an
  analogous `UNKNOWN`/`AMBER` badge, but that machinery is about
  EXPIRATION-CYCLE coverage, not single-session intraday shape, so it would
  need its own (parallel, not reused-verbatim) implementation. **Inference**
  on the design-pattern transfer; the existing code itself is
  **Repo-verified**.
- **Liquidity-gate cadence mismatch.** `passes_liquidity()` is evaluated
  against whichever single daily chain snapshot is loaded (per the file's own
  `main()` loop, which reads the latest cached `.cache/chains/{symbol}_*.parquet`
  file) — i.e., under the current once/few-times-per-day cadence there is no
  intraday-timing counterpart anywhere in the scanner today. A volume-
  periodicity/RVOL signal would be additive on the TIMING axis (nothing
  currently answers "when in the session"), while remaining entirely outside
  the option-leg liquidity fields (OI/spread) that `passes_liquidity()` checks.

---

## 10. QuantConnect source record

**Target URL:** `https://www.quantconnect.com/research/21066/intraday-volume-periodicity/p1`

Three WebFetch attempts were made with different prompts (a general-content
summary, a verbatim-metadata check, and a formula-extraction check). All three
returned content (no hard block/login-wall/404 was reported), and the
strategy-level formulas (`r_i = 1 + e_i/max_j(e_j)`, `w_i = r_i/Σ_j(r_j)`) were
reproduced **identically** across two independent calls — a reasonable
internal-consistency signal for content that IS present on the page.

However, **WebFetch is an AI-summarization tool over fetched HTML, not a
verbatim quoting tool** (this repo's own CLAUDE.md documents WebFetch
returning a one-sentence summary for a page with ~10.5k characters of body
text elsewhere — the same caution applies here). Two specific details —
byline author "Rudy Osuna" and the citation "Wu, Zhang & Dai (2025)" — did NOT
appear in the first (general-summary) fetch and only appeared once a more
targeted prompt was used on the second/third fetch. Rather than accept these
at face value, I independently verified both via WebSearch:

- **"Rudy Osuna"** is a real, identifiable QuantConnect community
  contributor/Community Advisor (Triton Quantitative Trading, UC San Diego;
  independently found at `quantconnect.com/u/rudy-osuna`, a LinkedIn profile,
  and a separate, independently-search-confirmed QuantConnect research post
  he co-authored, `quantconnect.com/research/20371/...`, which sits in the
  same URL numbering scheme as the target page).
- **"Wu, Zhang & Dai (2025)"** is a real, independently locatable paper:
  *"Spectral Volume Models: Universal High-Frequency Periodicities in Intraday
  Trading Activities"* by Lintong Wu, Ruixun Zhang, and Yuehao Dai, published
  in *Management Science* (SSRN working-paper id 4230610), thematically an
  exact match for "intraday volume periodicity" via Fourier/spectral methods.

This cross-check makes outright fabrication of the whole page unlikely, but I
was **not able to independently verify the page's exact numeric backtest
claims** (a Sharpe ratio of ~0.792 vs. ~0.406 for SPY over a stated
"July 2021–July 2026" window) against any second source — a direct SSRN PDF
fetch returned **HTTP 403 Forbidden**, and no WebSearch query surfaced an
independent quote of the QuantConnect page's own backtest numbers. **Per the
task's evidence standard, those specific performance figures are recorded here
as WebFetch-summarized content of moderate-but-not-fully-independently-
verified confidence, not as an Official-source-confirmed fact** — treat the
Sharpe-ratio figures, the "Spectral Tick-Flow Signal" dataset name, and the
exact field names (`volume_variance_explained`,
`volume_dominant_period_seconds`, `execution_score`) as **plausible and
internally consistent across repeated fetches, but not verbatim-confirmed
against a second independent source.**

No instructions embedded in any fetched page content were followed; all
fetched web content was treated as untrusted data per task instructions.

---

## 11. Local QuantConnect / Lean clone check

Checked via read-only `find`/`ls` under both
`/Users/carsynstephenson/options-validator` (maxdepth 4) and
`/Users/carsynstephenson` (maxdepth 2), searching for `*lean*`, `*quantconnect*`,
and `qc*` (case-insensitive).

**Result: no local QuantConnect or Lean engine clone exists.** The only hits
were false-positive **substring** matches, not real Lean/QuantConnect
artifacts:

- `node_modules/lodash/isBoolean.js`, `node_modules/lodash/fp/isBoolean.js`,
  `node_modules/figlet/importable-fonts/Lean.js`,
  `node_modules/figlet/importable-fonts/Lean.d.ts`,
  `node_modules/figlet/fonts/Lean.flf` — an npm-installed ASCII-art font
  literally named "Lean" (a figlet font style), unrelated to QuantConnect's
  Lean trading engine.
- `.tmp/carsyn-portfolio/node_modules/is-boolean-object` — matched the `qc*`
  pattern only spuriously (does not actually start with "qc"; a find
  operator-precedence artifact, not a real hit).
- `/Users/carsynstephenson/.claude/.last-cleanup` and
  `/Users/carsynstephenson/.crawl4ai/cleaned_html` — matched `*lean*` only
  because "clean"/"cleaned" contains the substring "lean" (c-**lean**-up,
  c-**lean**-ed); not Lean/QuantConnect directories.

No directory named `Lean`, `QuantConnect`, or a `qc*`-prefixed project
directory was found in either location. **Repo-verified absence** (direct
`find`/`ls` output, this session).

---

## 12. Source log

| # | Title / description | Publisher / author | URL | Pub. date | Access date | Claim supported | Excerpt / paraphrase | Confidence & limitations |
|---|---|---|---|---|---|---|---|---|
| 1 | "Intraday Volume Periodicity" (target research page) | QuantConnect.com; byline "Rudy Osuna" (per targeted WebFetch) | https://www.quantconnect.com/research/21066/intraday-volume-periodicity/p1 | Not stated on page | 2026-07-24 | Hypothesis (§1), formulas (§2c/2d), inputs (§3) | "Periodic trading carries more information content, so investors face greater adverse selection and demand a higher return..."; `r_i = 1 + e_i/max_j(e_j)`, `w_i = r_i/Σ_j(r_j)`; fields `volume_variance_explained`, `volume_dominant_period_seconds`, `execution_score`; reported Sharpe 0.792 vs 0.406, July 2021–July 2026 | **Official-source, moderate confidence.** WebFetch is AI-summarized (repo's own CLAUDE.md notes it is not verbatim). Fetched 3x with consistent core formulas; author and cited paper independently corroborated via WebSearch (see rows 4, below). Exact numeric backtest figures and dataset name NOT independently corroborated by a second source; direct SSRN fetch of the underlying paper returned 403. |
| 2 | "An Investigation of Transactions Data for NYSE Stocks" | Wood, R.A.; McInish, T.H.; Ord, J.K. — *Journal of Finance* 40(3), 723–739 | https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1985.tb04996.x | July 1985 | 2026-07-24 | Hypothesis §1 (original U-shape empirical finding) | "unusually high returns and standard deviations of returns found at the beginning and the end of the trading day" (WebSearch-derived paraphrase of abstract/summary) | **Official-source, moderate confidence** — citation (journal, volume, pages, year) independently confirmed via two separate WebSearch results (repec.org and Wiley); exact article text not directly fetched, only search-engine-summarized excerpts. |
| 3 | "A Theory of Intraday Patterns: Volume and Price Variability" | Admati, A.R.; Pfleiderer, P. — *Review of Financial Studies* 1(1), 3–40 | https://academic.oup.com/rfs/article-abstract/1/1/3/1601212 (also gsb-faculty.stanford.edu/anat-r-admati) | 1988 | 2026-07-24 | Hypothesis §1 (theoretical mechanism); Section 6 (regime dependence of the mechanism) | "concentrated-trading patterns arise endogenously as a result of the strategic behavior of liquidity traders and informed traders"; documents the U-shape of average volume | **Official-source, moderate confidence** — citation confirmed across multiple independent sources (SciRP, RePEc, Semantic Scholar, Stanford GSB faculty page, Oxford Academic); full text not directly fetched, only WebSearch-summarized abstract/description. |
| 4 | "Spectral Volume Models: Universal High-Frequency Periodicities in Intraday Trading Activities" | Wu, Lintong; Zhang, Ruixun; Dai, Yuehao — *Management Science* (2024/2025); SSRN working paper 4230610 | https://pubsonline.informs.org/doi/10.1287/mnsc.2024.06215 ; https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4230610 | 2024–2025 (Management Science publication cycle) | 2026-07-24 | Formulas §2c (spectral/periodogram methodology); corroborates the QuantConnect page's cited academic basis (§10) | "We develop spectral volume models to systematically estimate, explain, and exploit the high-frequency periodicity in intraday trading activities using Fourier analysis." Periodogram-based approach; dominant frequency components explain a substantial portion of intraday volume variation; attributed to algorithmic execution. | **Official-source, moderate confidence.** Published-journal abstract page (pubsonline.informs.org) fetched successfully via WebFetch (AI-summarized). Direct SSRN PDF fetch returned **HTTP 403 Forbidden** — full paper text NOT read; only the abstract-level paraphrase was obtained. |
| 5 | "Relative Daily Volume" indicator documentation | QuantConnect.com (official docs) | https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators/relative-daily-volume | Not stated | 2026-07-24 | Formulas §2b (RVOL normalization formula) | "Current volume from open to current time of day / Average over the past x days from open to current time of day"; code example `RDV(symbol, 2)` | **Official-source, higher confidence** — official documentation page, formula quoted directly by WebFetch as page text, not a research/blog claim; still summarized by an AI fetch tool rather than raw HTML re-read, so treat exact code example (`, 2`) as representative but not independently re-verified byte-for-byte. |
| 6 | `config.py` | This repo | `/Users/carsynstephenson/options-validator/config.py` | N/A (repo file, current HEAD at task time) | 2026-07-24 | Section 9 overlap analysis; Section 7 split-handling caution (STUDY_ERA_START/AMZN note); Section 6 universe composition | Full file read directly (Read tool); no volume-based constant exists; `MIN_OPEN_INTEREST`/`MAX_SPREAD_PCT` are option-leg liquidity fields; `rv21`/IV-rank/VRP-proxy constants (`H5_IVR_*`, `H5_VRP_SELL_GREEN`) are the closest related family; AMZN close series kept raw/strike-aligned to avoid the 2022-06 20:1 split reading as a spurious cycle | **Repo-verified** — direct file read, this session. |
| 7 | `options_researcher/attractiveness.py` | This repo | `/Users/carsynstephenson/options-validator/options_researcher/attractiveness.py` | N/A (repo file, current HEAD at task time) | 2026-07-24 | Section 9 overlap analysis (liquidity-gate cadence, earnings-cycle badge pattern) | Full file read directly (Read tool); `passes_liquidity()` imported from `data.thetadata_adapter`, checked against a single loaded daily chain snapshot in `main()`; `ladder_cards()`/`earnings_in_cycle`/`earnings_unknown` implement a fail-visible UNKNOWN-over-false-GREEN pattern gated by `config.EARNINGS_COVERAGE_DAYS` | **Repo-verified** — direct file read, this session. |
| 8 | `.research/00_baseline.md` | This repo (prior/sibling research-workstream file) | `/Users/carsynstephenson/options-validator/.research/00_baseline.md` | 2026-07-24 (session file) | 2026-07-24 | Section 4 (live-data entitlement gap: 5 snaps/day, stock/greeks endpoints not entitled, parity-derived spot) | "the live scanner runs 5 snaps/day on ThetaData; stock/greeks endpoints NOT entitled — spot comes from options parity. Any intraday *stock volume* requirement is therefore a NEW data dependency, not a covered one. To be verified by the licensing researcher, not assumed." | **Repo-verified that the file makes this claim**; the underlying entitlement fact is explicitly flagged BY THAT FILE as not yet independently verified — carried forward here with the same caveat, not upgraded to a harder confidence level. |
| 9 | Local filesystem search for a QuantConnect/Lean clone | N/A (direct tool output) | N/A | N/A | 2026-07-24 | Section 11 | `find`/`ls` output showing only false-positive substring matches (figlet "Lean" font, "clean(ed)" substrings); no real Lean/QuantConnect directory | **Repo-verified absence** — direct command output, this session. |

---

**Unresolved evidence gaps (carried into the file itself, not just the reply):**
direct SSRN full-text of Wu/Zhang/Dai (2025) was blocked (403); the
QuantConnect target page's exact numeric backtest results and its
"Spectral Tick-Flow Signal" dataset name could not be independently
corroborated beyond the (AI-summarized) WebFetch content itself; the
underlying live-entitlement fact in Section 4 is inherited from a sibling
research file that itself marks it as unverified.
