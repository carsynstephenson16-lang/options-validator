# Scanner-signal candidates: intraday volume periodicity and alternatives

**Research cutoff / access date:** 2026-07-24. **Scope:** research-only scoring
note. No code written, no config changed, no file edited other than this one.
Evidence labels used throughout: **Official-source**, **Repo-verified**,
**Inference**, **Assumption** (per this repo's claim-discipline rule).
Vocabulary discipline observed: no "proven/confirmed/works/edge found/
guaranteed" language about any backtest.

This file is a sibling of two other read-only research notes already on disk
in this directory — `.research/00_baseline.md` (repo/branch/entitlement
baseline) and `.research/01_periodicity.md` (a deep, independently-produced
dive on the anchor candidate alone, including a rigorous three-fetch
cross-check of the target QuantConnect page). Where this file's own
verification overlaps that prior work, it is cited rather than re-derived, to
avoid duplicating an already-careful pass; the six-dimension scoring and the
candidate comparison across five signals are this file's own, original
contribution.

---

## Method

1. **Repo read (read-only, this session):** `config.py`, `options_researcher/
   attractiveness.py`, `data/thetadata_adapter.py`, `options_researcher/
   live_quotes.py`, `options_researcher/features.py` (grep), and
   `docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md` — to
   establish, **Repo-verified**, exactly what the scanner already computes,
   what data the ThetaData subscription actually delivers today (both the
   historical/backtest path and the live 5-snapshot path), and what the
   already-committed RQ2 badges (B1 term-structure, A1 bounce, C1 board
   concentration, N3-1 market-implied lines, V1 VRP-calibration, H1 hygiene)
   already claim, so new candidates can be scored for genuine orthogonality
   rather than guessed.
2. **Web research (WebSearch + WebFetch):** the named QuantConnect research
   post on intraday volume periodicity, QuantConnect's own documentation and
   strategy-library pages for closely related signals, and independently
   corroborated peer-reviewed / working-paper literature for every candidate.
   Every web claim is labeled for confidence; anything I could not
   independently corroborate against a second source is flagged as such
   rather than presented as fact. All fetched page content was treated as
   untrusted data — no instructions embedded in any fetched page were acted
   on.
3. **Scoring:** each candidate is scored 0–5 (integer) on six dimensions.
   **Explicit convention for "Overfitting and leakage risk" (per task
   instruction): higher score = LOWER risk.** A 5 means the construction is
   simple, causal by design, has a long or independently-replicated
   out-of-sample record, and involves few researcher degrees of freedom
   (few arbitrary choices of window/threshold/strike). A 0 would mean the
   opposite: many arbitrary construction choices, a short or single-path
   backtest, or a widely-publicized effect with documented post-publication
   decay risk. No candidate here scores at either extreme; all sit in the
   1–4 band, which is itself an honest reflection of how much design
   discipline any of these would need before registration.
4. **Selection rule followed:** per the task's instruction, no candidate is
   promoted to lead solely because of a reported backtest number. The lead
   selection below is argued from economic mechanism plus this repo's actual
   data feasibility and implementation fit; backtest figures (where they
   exist at all) are treated as, at most, weak corroborating color.

---

## Candidate list

| ID | Candidate | Category |
|---|---|---|
| **C1** | Intraday volume periodicity / relative-volume-vs-time-of-day (**anchor**, per task) | New equity data required |
| **C2** | Options open-interest change / unusual OI build-up | Already-entitled options-snapshot data |
| **C3** | Put/call ratio dynamics (OI-based today; volume-based needs a new-but-same-subscription endpoint) | Already-entitled options-snapshot data |
| **C4** | Option-implied-volatility skew steepness (OTM-put skew slope) | Already-entitled options-snapshot data / literature-derived |
| **C5** | First-half-hour → last-half-hour intraday return momentum | QuantConnect-derived / literature-derived, new equity data required |

Five candidates: the anchor (C1) is included as required; C2 and C3 satisfy
"computable from already-entitled ThetaData options snapshots, no new data";
C4 and C5 satisfy "QuantConnect-research-derived or academic candidate," and
C4 additionally sits inside the entitled-data category, giving two
independent, non-duplicative ways of meeting that requirement.

---

## Per-candidate scores and justifications

### Score table

| Candidate | Economic rationale | Free live-data availability | Orthogonality | Relevance to options selection | Repo implementation fit | Overfitting/leakage risk (5 = lowest risk) | **Total /30** |
|---|---|---|---|---|---|---|---|
| C1 — Intraday volume periodicity / RVOL (anchor) | 4 | 1 | 5 | 2 | 1 | 2 | 15 |
| C2 — Options OI-change / unusual build-up | 3 | 4 | 5 | 5 | 5 | 3 | **25** |
| C3 — Put/call ratio dynamics | 3 | 2 | 4 | 3 | 3 | 3 | 18 |
| C4 — IV skew steepness (OTM-put skew) | 4 | 5 | 4 | 5 | 4 | 2 | 24 |
| C5 — First/last half-hour intraday momentum | 4 | 1 | 5 | 2 | 1 | 2 | 15 |

The total column is a simple sum shown for orientation only — it is not the
selection rule (see "Lead candidate selection" below, which argues from
mechanism and feasibility, not from the arithmetic total, per the task's own
instruction not to let a single number carry the decision).

---

### C1 — Intraday volume periodicity / relative volume vs. time-of-day (ANCHOR)

**What it is:** the hypothesis, named directly in the task, that intraday
trading volume is not flat across the session and that (a) how far
today's cumulative volume-at-time-t deviates from the name's own historical
volume-at-time-t ("relative volume," RVOL), and/or (b) how much of a name's
intraday volume is explained by a small number of recurring high-frequency
cycles ("periodicity strength"), carries information.

**Economic rationale — 4/5.** The base empirical fact (volume is U-shaped
across the session) and its leading theoretical explanation are old,
peer-reviewed, and independently corroborated across multiple search hits:
Wood, McInish & Ord (1985, *Journal of Finance*) documented the empirical
U-shape on NYSE transactions data; Admati & Pfleiderer (1988, *Review of
Financial Studies*) modeled WHY it arises (discretionary liquidity traders
cluster to hide behind each other; informed traders then camouflage inside
that same clustering). A modern, independently-corroborated extension — Wu,
Zhang & Dai, "Spectral Volume Models: Universal High-Frequency Periodicities
in Intraday Trading Activities" (*Management Science*, 2024/2025; SSRN
4230610) — uses Fourier/spectral methods to show persistent high-frequency
periodicity attributable to algorithmic execution schedules. **Official-source**
(citations independently corroborated via multiple search hits per
`.research/01_periodicity.md` §12). The specific claim the target QuantConnect
page makes — that periodicity STRENGTH itself carries a cross-sectional
return premium via adverse selection — is a step beyond what any of the three
academic papers directly establish; that extension is **Inference**, not an
independently-replicated academic result. Score is 4, not 5, because the
options-selection bridge (see below) is not established by any source found.

**Free live-data availability — 1/5.** **Repo-verified** (this repo's
`config.py`, `data/thetadata_adapter.py`, and `options_researcher/
live_quotes.py`; corroborated independently by `.research/00_baseline.md` and
`.research/01_periodicity.md` §4): this repo's ThetaData entitlement covers
options-chain endpoints (`option_history_greeks_eod`,
`option_history_open_interest` historically; `option_snapshot_quote`,
`option_snapshot_greeks_all`, `option_snapshot_open_interest` live) and
explicitly does NOT cover a live equity/stock feed — live spot is derived via
put-call parity precisely because a direct stock quote is not entitled. A
volume-periodicity signal needs a **continuous or near-continuous, full-session
equity share-volume feed**, which is a strictly harder ask than a single daily
number and does not exist anywhere in this repo's current data access. This
would be an entirely new, free-for-live-use data dependency that does not
currently exist. Score 1, not 0, because a much coarser, once-daily
DESCRIPTIVE version (comparing today's total volume to trailing history) could
in principle be built from a free EOD volume source without an intraday feed
— a materially weaker, different use case than the named anchor.

**Orthogonality — 5/5.** **Repo-verified**: grep of `options_researcher/
features.py` and a full read of `config.py` and `attractiveness.py` found no
equity share-volume constant, feature, or badge anywhere in the scanner today
(the only volume-adjacent fields are `open_interest`, an **option-contract**
field checked once per liquidity gate, not equity share volume). None of the
RQ2 briefs (B1 term-structure, A1 bounce, C1 concentration, N3-1
market-implied lines, V1 VRP-calibration) touch volume or intraday timing at
all. This is a genuinely new axis.

**Relevance to options selection — 2/5.** This is fundamentally an
equity-liquidity/execution-timing signal, not an options-pricing signal.
Per `.research/01_periodicity.md` §8 (an independent pass I did not need to
redo): the strongest defensible bridge is EXECUTION TIMING — using RVOL to
decide *when* in a session quotes are most trustworthy — which interacts with
this repo's "fill at mid or worse" cost model but says nothing about *which*
strike, expiry, or structure to prefer. No source found ties volume
periodicity to option-implied volatility, skew, or directional bias.

**Repository implementation fit — 1/5.** Would require a wholly new data
ingestion pipeline (a new, currently-nonexistent free intraday-equity-volume
provider), a new no-look-ahead rolling-profile store, and a new cadence
(continuous, not the existing few-times-daily scanner run) — a large
departure from "every number lives in `config.py`, nothing new unless it moves
a live hypothesis," and structurally mismatched with a scanner that runs a
handful of times per day rather than continuously.

**Overfitting and leakage risk — 2/5 (moderate-to-real risk).** The
construction has several well-identified, concrete leakage failure modes if
built carelessly: normalizing today's reading against a window that includes
today itself; dividing an intraday cumulative reading by that same day's
eventual close-of-day total (leaking the day's own outcome into every earlier
ratio); mis-handling holidays/half-days; and letting unadjusted volume across
a stock split manufacture a spurious "periodicity break" (this repo's own
`config.py` `STUDY_ERA_START` note on AMZN already treats exactly this class
of split-contamination risk for price series, so the caution is not
theoretical). The QuantConnect page's own reported outcome is a single
historical path for a 100-name, long-only cross-sectional factor — "not yet
rejected" at most for that specific construction, and silent on any
narrower, single-name or options-specific use.

---

### C2 — Options open-interest change / unusual OI build-up

**What it is:** a day-over-day (or rolling multi-day) change in a contract's
or strike-cluster's open interest, flagged when the build-up is large relative
to that name's own recent history — a proxy for new directional positioning
accumulating in specific strikes, adapted from the options-informed-trading
literature (which is built on VOLUME, not OI — see the honesty note below).

**Economic rationale — 3/5.** The underlying informed-trading mechanism has
real peer-reviewed support, but the specific literature is about option
**volume**, not open interest: Pan & Poteshman (2006, *Review of Financial
Studies*) find that low buyer-initiated put/call VOLUME ratios predict higher
next-day and next-week risk-adjusted returns, and attribute this to
non-public information held by option traders (**Official-source**, citation
independently corroborated across NBER, RFS, and multiple secondary sources).
Johnson & So (2012, *Journal of Financial Economics*) similarly find the
option-to-stock VOLUME ratio (O/S) predicts returns, strongest where
short-sale costs are high (**Official-source**, corroborated across SSRN,
ScienceDirect, and the authors' own posted PDF). An OI-based build-up signal
is a reasonable, mechanistically-adjacent extension (new positions must show
up in OI, not just volume), but it is a less-tested variant of the literature's
own construction — volume captures same-day round-trip activity that OI does
not, and OI also reflects unwinds and market-maker inventory changes that have
nothing to do with informed conviction. Score 3 reflects a plausible but
adapted (not directly-tested) mechanism.

**Free live-data availability — 4/5.** **Repo-verified**: `data/
thetadata_adapter.py` already calls `option_history_open_interest` for every
cached historical symbol-day (comment at lines 14-17 of that file states the
OI figure reflects the prior day's OPRA report and "is already known during
day D, so joining day-D OI is look-ahead-free" by the adapter's own design),
and `options_researcher/live_quotes.py`'s `REQUIRED_PROBE_ENDPOINTS` already
lists `option_snapshot_open_interest` among the endpoints the live 5-snapshot
lane requests. No new endpoint, no new subscription, no new cost. Score 4,
not 5, only because this repo's own memory record flags that the account's
live entitlement has previously denied some non-quote endpoints (stock,
greeks) outright, so live-side OI availability, while requested today, is not
100% confirmed working in production — an honest residual uncertainty, not a
new-data problem.

**Orthogonality — 5/5.** **Repo-verified**: today's only use of
`open_interest` anywhere in the scanner is a static per-contract liquidity
threshold (`config.MIN_OPEN_INTEREST`, checked via `passes_liquidity()` in
`data/thetadata_adapter.py` and called from `attractiveness.py`) — a level
check, never a change/flow signal. Nothing in `config.py`, `attractiveness.py`,
or the RQ2 briefs computes a day-over-day OI delta or flags unusual OI
build-up. This is a new axis with zero code-level overlap.

**Relevance to options selection — 5/5.** This is a per-contract, per-strike
signal computed on data the scanner already renders per card — it would sit
naturally as an additional badge next to the existing liquidity/earnings/VRP
badges on the same put/covered-call/PMCC cards, potentially flagging "recent
build-up at this strike" as context for a seller or buyer decision. Direct
fit to the existing card structure.

**Repository implementation fit — 5/5.** Needs only a rolling historical join
against data already fetched and cached (mirrors the design pattern already
used by the committed RQ2 Brief B1's causal-percentile construction) — a new
`features.py` column, a new frozen `config.py` threshold, and a test for the
causal property (truncating the cache at day D reproduces day-D values
exactly). No new provider, no new schema, no new live-entitlement risk beyond
what is already being requested.

**Overfitting and leakage risk — 3/5.** The base OI join is, by the adapter's
own documented design, look-ahead-free (the prior day's OPRA report is known
before day D trades). That is a real point in this candidate's favor relative
to most others here. The risk that remains is in the DERIVED signal: choosing
a lookback window and a "build-up" threshold on a 14-name, discrete-strike
universe where absolute OI levels are often thin (the existing gate,
`MIN_OPEN_INTEREST = 100`, is itself a low bar), so a modest percentage jump
on a small base could easily be noise rather than genuine accumulation. A
pre-registered percentile-based threshold (rather than a hand-picked
percentage) would meaningfully reduce this risk, but that discipline has not
yet been applied to this specific candidate.

---

### C3 — Put/call ratio dynamics

**What it is:** an aggregate ratio of put activity to call activity for a
name (classically built from VOLUME; here, given this repo's actual data,
most readily built from OPEN INTEREST), watched for extremes or for a
change over time, as a contrarian-sentiment / positioning-skew gauge.

**Economic rationale — 3/5.** The strongest academic support (Pan &
Poteshman 2006, cited above) is specifically for a put/call ratio built from
BUYER-INITIATED VOLUME, not aggregate open interest — this repo does not
currently fetch option volume at all (see the honesty note on data
feasibility below), so the readily-buildable OI-based variant is an adaptation
of the tested construction, not a replication of it. Separately, the
put/call ratio (in any construction) is also one of the most widely
publicized "textbook" contrarian sentiment indicators in retail and
practitioner literature, which raises genuine doubt about how much
un-arbitraged signal remains in a naive level-based version: McLean & Pontiff
(2016, *Journal of Finance*) find that portfolio returns for published
cross-sectional predictors decline 26% out-of-sample and 58%
post-publication on average, consistent with informed trading eroding known
effects (**Official-source**, citation independently corroborated across
Wiley, SSRN, and RePEc). Score 3 reflects a real but adapted/partially-eroded
mechanism.

**Free live-data availability — 2/5.** **Repo-verified**: `data/
thetadata_adapter.py`'s `CHAIN_COLUMNS` schema (`expiration, strike, right,
bid, ask, open_interest, iv, delta, gamma, theta, vega`) contains no volume
field at all, and neither the historical fetch (`_fetch_raw`, calling only
`option_history_greeks_eod` + `option_history_open_interest`) nor the live
snapshot lane's `REQUIRED_PROBE_ENDPOINTS` (`option_snapshot_quote`,
`option_snapshot_greeks_all`, `option_snapshot_open_interest`) request
options volume. The installed `thetadata` Python client DOES expose
`option_history_trade` and `option_snapshot_trade` methods (**Repo-verified**
via direct inspection of the installed package at
`.venv/lib/python3.12/site-packages/thetadata/client.py`), so a true
volume-based ratio would use the SAME subscription and cost no new money —
but it is not currently wired into this repo, and whether this account's
specific entitlement tier actually authorizes that endpoint (as opposed to
just quote/greeks/OI) is unverified (**Assumption**, given this repo's own
memory record that some non-quote endpoints have been denied for this account
before). The OI-based variant needs no new endpoint at all. Score reflects the
mixed picture: workable today in a weaker form, genuinely new engineering (and
an unconfirmed entitlement) for the literature's actual tested form.

**Orthogonality — 4/5.** **Repo-verified**: no put/call ratio of any kind
exists in `config.py`, `attractiveness.py`, or the RQ2 briefs today. Scored
one point below C2/C4 because it sits conceptually closer to the existing
"is premium rich" framing already covered by `H5_VRP_SELL_GREEN` /
`iv_minus_rv` and IV-rank badges (both are also, at bottom, "which side is
paying/positioned more" questions), even though there is no shared code or
formula.

**Relevance to options selection — 3/5.** It is a symbol-level aggregate
(one number per name per day), not a per-contract signal, so it fits less
naturally onto the existing per-strike card structure than C2 or C4; its
best use would be board-level context (similar in spirit to the already-
committed Brief C1 concentration panel) rather than a per-card badge.

**Repository implementation fit — 3/5.** The OI-based version fits easily
(same pattern as C2); the volume-true version needs a new endpoint,
schema extension, and an entitlement check before it could be trusted live.

**Overfitting and leakage risk — 3/5.** Constructed from same-day aggregated
data, the ratio itself is simple and causal if computed end-of-day. The risk
is less about look-ahead and more about signal decay: put/call ratio is a
famous, decades-publicized indicator, and per McLean & Pontiff's general
finding, well-known cross-sectional predictors show measurable post-publication
return decay — a level-based threshold "discovered" by backtesting this
repo's own small universe risks re-finding a well-known, partially-eroded
pattern rather than new information.

---

### C4 — Option-implied-volatility skew steepness (OTM-put skew slope)

**What it is:** the slope of implied volatility across STRIKES at a fixed
tenor (e.g., a 0.20-delta put's IV minus the at-the-money IV, or an
equivalent moneyness-based slope) — distinct from the already-committed RQ2
Brief B1, which measures a TENOR slope (near-dated IV minus far-dated IV) at
fixed moneyness. Skew asks "how much extra does far-OTM downside protection
cost relative to at-the-money," not "how does IV compare across expiries."

**Economic rationale — 4/5.** Xing, Zhang & Zhao (2010, *Journal of
Financial and Quantitative Analysis*) is a well-cited, peer-reviewed,
cross-sectional finding (**Official-source**, citation independently
corroborated across Cambridge Core, SSRN, and multiple secondary sources):
steeper individual-equity-option volatility smirks predict lower future
equity returns, with the authors' own stated interpretation being that
informed traders with negative private information prefer to trade
out-of-the-money puts, and the equity market is slow to fully incorporate
that information. This is a direct, well-documented, informed-trading-based
mechanism from a top finance journal. Not a 5 because the original result is
a broad cross-sectional (many-hundred-stock) finding; applying it to a
concentrated 14-name AI-infrastructure universe is an out-of-sample
extrapolation the original paper does not itself test.

**Free live-data availability — 5/5.** **Repo-verified**: skew needs only
per-contract `iv`, `delta`, and `strike` at a single date for a single tenor —
every field already lives in the cached EOD chain schema
(`data/thetadata_adapter.py` `CHAIN_COLUMNS`) and is already read by
`attractiveness.py`'s card builders (e.g., `_vol_prose()`, the delta-nearest
selection logic in `put_card_rows`/`cc_card_rows`). Genuinely zero new data,
zero new endpoints, zero new entitlement risk.

**Orthogonality — 4/5.** **Repo-verified**: no strike-dimension skew measure
exists anywhere in `config.py` or `attractiveness.py` today. This is
carefully distinguished from the already-committed RQ2 Brief B1
(`ts_slope = atm_iv_near − atm_iv_long`, a same-moneyness, cross-tenor
measure) — B1 slices the vol SURFACE along the tenor axis, this candidate
slices it along the moneyness/strike axis. A genuinely new dimension, though
one point is docked because both this candidate and B1 sit under the same
general "shape of the vol surface" family and would need careful, distinct
naming/display so a reader does not conflate "term-structure corner" with
"skew steepness."

**Relevance to options selection — 5/5.** Directly usable: it is computed
from the exact per-contract fields the scanner already ranks candidates by
(IV, delta, strike), on the exact per-name cards already rendered, and the
published effect concerns future EQUITY returns — directly relevant context
for a seller (put-credit / covered-call) or buyer (long-call/LEAPS) already
choosing a strike from that same chain.

**Repository implementation fit — 4/5.** Straightforward: pick two reference
points on the already-cached chain (e.g., the existing H5-income-delta put vs.
the nearest at-the-money strike), compute a slope, and mirror the
already-designed causal-percentile pattern from Brief B1 (rolling trailing
window, minimum-observation refusal, "no future rows leak" test). Not a 5
because the specific strike/delta convention chosen is itself a design
decision that needs a frozen, disclosed definition before any code is
written — more moving parts than C2's simple day-over-day diff.

**Overfitting and leakage risk — 2/5.** The published effect is a
cross-sectional, many-stock result; this repo's own 14-name, single-thesis,
AI-infrastructure-concentrated universe is a much smaller and noisier sample
in which to look for the same pattern, and skew-slope construction has
several genuinely arbitrary choices (which strike/delta pair, which tenor)
that invite quietly re-specifying the definition until a backtest looks
better — exactly the class of researcher-degrees-of-freedom risk this repo's
own pre-registration discipline (ledger-discipline: freeze parameters before
viewing results) exists to guard against.

---

### C5 — First-half-hour → last-half-hour intraday return momentum

**What it is:** the documented pattern that a name's (or the market's)
return in the first ~30 minutes of a session predicts the sign of its return
in the last ~30 minutes of the same session.

**Economic rationale — 4/5.** Gao, Han, Li & Zhou (2018, *Journal of
Financial Economics*) is a well-cited, peer-reviewed finding on ETF data
(SPY/IWM/IYR, 1993–2013): the first half-hour return predicts the last
half-hour return, stronger on more volatile days, higher-volume days,
recession days, and macro-news days (**Official-source**, citation
independently corroborated across ScienceDirect, SSRN, and the authors'
posted PDFs). QuantConnect's own "Intraday ETF Momentum" strategy-library
page independently and consistently describes the same mechanism and cites
the same underlying research when directly fetched, which corroborates that
this is a real, documented pattern rather than a one-off claim. Not a 5
because the tested universe is broad index ETFs, not single-name equities or
options.

**Free live-data availability — 1/5.** Needs live or near-live intraday
MINUTE-level equity price data for all 14 names, continuously through the
session — the same fundamental gap as C1 (**Repo-verified**, same entitlement
facts as above: no live stock feed, only options-derived, discrete,
periodic parity-spot snapshots). A same-day open-to-close signal cannot be
built from 5 discrete daily option snapshots; it needs a genuinely new,
continuous, free equity feed.

**Orthogonality — 5/5.** No intraday-return signal of any kind exists in
this repo today; the closest existing feature, `mom_1m` (a ~21-session,
multi-day momentum window per `config.TECH_MOM_1M`), operates on an entirely
different timescale and has zero code-level overlap.

**Relevance to options selection — 2/5.** Like C1, this is fundamentally a
same-day equity directional-timing signal on index-level ETFs in the
original research; translating a same-day open-to-close return-continuation
signal into which STRIKE, EXPIRY, or STRUCTURE to select is not established
by anything found, and the original literature's own universe (broad market
ETFs) is a further step removed from this repo's single-name,
AI-infrastructure-thesis options board than even C1's equity-volume
literature is.

**Repository implementation fit — 1/5.** Requires the same new
intraday-equity-data plumbing as C1, plus a same-day, two-observation
(first-half-hour, last-half-hour) construction that does not naturally fit a
scanner that runs a handful of times per day rather than continuously through
the session — poor fit on both the data-access and the operating-cadence
dimensions.

**Overfitting and leakage risk — 2/5.** The original paper's own
out-of-sample record spans two decades on liquid index ETFs, which is a
genuine point in its favor; the risk here is almost entirely about
extrapolation — applying a published, index-level, ETF-tested effect to 14
single, concentrated, higher-beta AI-infrastructure names is an untested
generalization, and constructing the "first/last half hour" windows
correctly from only 5 discrete daily snapshots (rather than a continuous
feed) invites subtle window-definition and look-ahead bugs that the original
paper's continuous-data setting never had to solve.

---

## Lead candidate selection

**Lead: C2 — options open-interest change / unusual OI build-up.**

Reasoning, argued from mechanism and feasibility (not from any backtest
number — no candidate here carries a backtest result strong enough, or
independently verified enough, to argue from in the first place):

- It is the only candidate that needs **zero new data and zero new
  endpoints**: the day-over-day OI join this candidate depends on is already
  fetched, already cached, and already documented by this repo's own adapter
  as look-ahead-free by construction (`data/thetadata_adapter.py` lines
  14-17). Every other candidate either needs a new equity-data relationship
  entirely (C1, C5) or needs a new-but-unconfirmed endpoint on the options
  side (C3's volume-true form).
- It has the cleanest, most direct fit to a per-contract signal on the
  exact cards the scanner already renders (put/covered-call/PMCC), mirroring
  the design pattern already used by the committed, owner-reviewed RQ2 Brief
  B1 (a new computed column, a frozen config threshold, a causal-percentile
  test) — this is new engineering the repo has already shown it knows how to
  do safely and cheaply.
- Its economic mechanism (informed positioning showing up as new open
  interest) is a plausible, literature-adjacent extension of a real,
  peer-reviewed finding (Pan & Poteshman 2006; Johnson & So 2012), honestly
  scored one point below a "directly tested" mechanism because those papers
  use volume, not OI — that gap is disclosed, not hidden, and does not by
  itself disqualify the candidate.
- Its main risk — thin absolute OI levels on a 14-name board making a
  percentage-based build-up threshold noisy — is a known, nameable,
  design-time problem (solvable with a percentile-based rather than a
  hand-picked threshold, following the B1 precedent) rather than a
  fundamental data or mechanism problem.

C4 (IV skew steepness) is the closest competitor and has, if anything, the
single strongest peer-reviewed economic mechanism of the five (Xing, Zhang &
Zhao 2010 is a direct, well-cited finding on exactly this repo's asset class
— single-name equity options). It is not selected as lead because (a) it
requires more new, not-yet-frozen design choices (which strike/delta pair,
which tenor) before it could be pre-registered responsibly, and (b) applying
a broad, many-hundred-stock cross-sectional finding to this repo's
concentrated 14-name universe is a real external-validity question that
deserves its own explicit design memo — the same posture this repo's own RQ2
process already took toward Brief N3-1 ("this brief IS the one-page spec for
the owner to nod at"). That makes it the strongest runner-up, not a weaker
candidate.

## Runner-up for the ideas parking lot

**Runner-up: C4 — option-implied-volatility skew steepness (OTM-put skew
slope).** This is named here as the recommended parking-lot entry (per task
instruction, `ideas-parking-lot.md` itself is NOT edited by this file). The
parking-lot note should record: strong peer-reviewed mechanism (Xing, Zhang &
Zhao 2010) distinct from the already-committed term-structure badge (Brief
B1); zero new data required; needs a frozen strike/delta/tenor convention and
an explicit small-universe external-validity discussion before design, i.e.
it should follow the same "owner-nod one-page spec" path Brief N3-1 already
established, not skip straight to implementation.

---

## Source log

| # | Title / description | Publisher / author | URL | Pub. date | Access date | Claim supported | Excerpt / paraphrase | Confidence & limitations |
|---|---|---|---|---|---|---|---|---|
| 1 | "Intraday Volume Periodicity" (QuantConnect target research page) | QuantConnect.com; byline "Rudy Osuna" per a targeted fetch | https://www.quantconnect.com/research/21066/intraday-volume-periodicity/p1 (my own initial fetch used the bare numeric URL `https://www.quantconnect.com/research/21066` without the slug and returned a similarly-themed but not verbatim-identical summary; see limitations) | Not stated on page | 2026-07-24 | C1 hypothesis and economic-rationale framing | "Periodic trading carries more information content, so investors face greater adverse selection and demand a higher return to hold the most periodic stocks"; reported Sharpe ~0.792 vs ~0.406 for SPY, July 2021–July 2026 window; a named "Spectral Tick-Flow Signal" dataset with fields `volume_variance_explained`/`execution_score` | **Official-source, moderate confidence.** My own single fetch (wrong/bare URL) could not be corroborated against the QuantConnect research index page, which returned "No Results" when fetched directly — on its own this would read as a fabrication risk. However, the sibling file `.research/01_periodicity.md` (this session, same repo) performed three separate WebFetch calls against the correctly-slugged URL and independently corroborated two specific, checkable details via WebSearch: the byline author "Rudy Osuna" is a real, identifiable QuantConnect community contributor with a second, separately-findable research post in the same URL-numbering scheme, and the cited paper "Wu, Zhang & Dai (2025)" is a real, independently locatable *Management Science* paper (SSRN 4230610). That cross-check makes outright fabrication of the whole page unlikely, but the exact numeric Sharpe figures and the specific dataset/field names remain **not independently corroborated by a second source** (a direct SSRN fetch of the underlying methodology paper returned HTTP 403). Treat the mechanism/framing as real; treat the specific performance numbers and dataset name as unverified. |
| 2 | Research-post confidence assessment (repo-internal) | This repo, prior sibling research file, same session | `/Users/carsynstephenson/options-validator/.research/01_periodicity.md` §10, §12 | 2026-07-24 (session file) | 2026-07-24 | Row 1's confidence characterization; carried forward rather than re-derived | See excerpt in row 1; the sibling file's own conclusion: "this cross-check makes outright fabrication of the whole page unlikely... [but] those specific performance figures are recorded here as WebFetch-summarized content of moderate-but-not-fully-independently-verified confidence" | **Repo-verified** that the file reaches this conclusion via a documented three-fetch, cross-checked methodology; adopted here rather than my own weaker single-fetch attempt. |
| 3 | Wood, R.A.; McInish, T.H.; Ord, J.K., "An Investigation of Transactions Data for NYSE Stocks" | *Journal of Finance* 40(3), 723–739 | https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1985.tb04996.x | 1985 | 2026-07-24 | C1 economic rationale (original empirical U-shape) | Documents unusually high returns and return variability at the open and close of the trading day relative to mid-session, on NYSE transactions data | **Official-source, moderate confidence** — citation independently confirmed across multiple search results (RePEc, Wiley); full text not directly fetched, only search-engine-level summary. |
| 4 | Admati, A.R.; Pfleiderer, P., "A Theory of Intraday Patterns: Volume and Price Variability" | *Review of Financial Studies* 1(1), 3–40 | https://academic.oup.com/rfs/article-abstract/1/1/3/1601212 | 1988 | 2026-07-24 | C1 economic rationale (theoretical mechanism) | Discretionary liquidity traders cluster trading in time to hide behind each other, reducing adverse-selection cost; informed traders then camouflage inside the same clusters, producing the endogenous volume U-shape | **Official-source, moderate confidence** — citation confirmed across multiple independent sources; abstract-level paraphrase only. |
| 5 | Wu, L.; Zhang, R.; Dai, Y., "Spectral Volume Models: Universal High-Frequency Periodicities in Intraday Trading Activities" | *Management Science* (2024/2025 publication cycle); SSRN 4230610 | https://pubsonline.informs.org/doi/10.1287/mnsc.2024.06215 | 2024–2025 | 2026-07-24 | C1 economic rationale (modern periodicity extension) | Fourier/spectral analysis showing persistent high-frequency periodicity in intraday volume, attributed to algorithmic execution schedules | **Official-source, moderate confidence** — published-journal abstract page corroborated across sources; direct SSRN PDF fetch returned HTTP 403 (not independently verified in full). |
| 6 | "Relative Daily Volume" indicator documentation | QuantConnect.com (official docs) | https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/supported-indicators/relative-daily-volume | Not stated | 2026-07-24 | C1 formula/mechanism grounding on the QuantConnect platform | "Current volume from open to current time of day / Average over the past x days from open to current time of day" | **Official-source, higher confidence** — official documentation page, formula quoted directly as page text by WebFetch. |
| 7 | "Opening Range Breakout for Stocks in Play" | QuantConnect.com research library | https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/ | Not stated | 2026-07-24 | Corroborates that QuantConnect's platform hosts real, literature-grounded relative-volume/time-of-day strategies (general credibility check on the research-library format) | Divides first-5-minute volume by the prior-14-day average first-5-minute volume to find "stocks in play"; recreation of Zarattini, Barbon & Aziz (2024) | **Official-source, higher confidence** — the underlying academic paper (SSRN 4729284, "A Profitable Day Trading Strategy For The U.S. Equity Market") was independently corroborated across nine-plus independent sources (SSRN, ResearchGate, Semantic Scholar, university repositories), giving strong confidence this specific QuantConnect page's content is genuine, unlike row 1's page. |
| 8 | "Market intraday momentum" | Gao, L.; Han, Y.; Li, S.Z.; Zhou, G. — *Journal of Financial Economics* 129(2), 394–414 | https://www.sciencedirect.com/science/article/abs/pii/S0304405X18301351 | 2018 | 2026-07-24 | C5 economic rationale | First half-hour return (from prior close) predicts the sign of the last half-hour return on SPY/IWM/IYR, 1993–2013; stronger on volatile/high-volume/recession/macro-news days | **Official-source, higher confidence** — citation and finding independently corroborated across ScienceDirect, SSRN, Semantic Scholar, and multiple university repository copies of the paper. |
| 9 | "Intraday ETF Momentum" | QuantConnect.com, Investment Strategy Library | https://www.quantconnect.com/learning/articles/investment-strategy-library/intraday-etf-momentum | Not stated | 2026-07-24 | C5 QuantConnect-platform grounding | "we observe the return generated from the first half-hour of the trading day to predict the sign of the trading day's last half-hour return"; recreates Gao/Han/Li/Zhou; reports annualized returns of 6.67% (SPY), 11.72% (IWM), 24.22% (IYR) in the original study | **Official-source, moderate-to-higher confidence** — content is internally consistent with, and independently corroborates, row 8's peer-reviewed paper; single WebFetch, not cross-verified via a second independent fetch of this specific page, but the underlying academic claim is independently solid. |
| 10 | Pan, J.; Poteshman, A.M., "The Information in Option Volume for Future Stock Prices" | *Review of Financial Studies* 19(3), 871–908 | https://academic.oup.com/rfs/article-abstract/19/3/871/1646711 ; https://www.mit.edu/~junpan/volume.pdf | 2006 | 2026-07-24 | C2 and C3 economic rationale | Buyer-initiated put/call VOLUME ratios predict returns: low-ratio stocks outperform high-ratio stocks by 40+ bps next day, 1%+ over the next week; effect attributed to non-public information | **Official-source, higher confidence** — citation and core finding corroborated across NBER, RFS/Oxford Academic, SSRN, and the author's own MIT-hosted PDF. |
| 11 | Johnson, T.L.; So, E.C., "The Option to Stock Volume Ratio and Future Returns" | *Journal of Financial Economics* 106(2), 262–286 | https://www.sciencedirect.com/science/article/abs/pii/S0304405X12000797 | 2012 | 2026-07-24 | C2 and C3 economic rationale | Lowest-decile O/S (option-to-stock volume ratio) firms outperform highest-decile by 0.34%/week (~19.3% annualized); O/S also predicts firm-specific earnings news, consistent with informed private information; effect strongest when short-sale costs are high | **Official-source, higher confidence** — corroborated across SSRN, ScienceDirect, the authors' own posted PDFs, and EconPapers. |
| 12 | Xing, Y.; Zhang, X.; Zhao, R., "What Does the Individual Option Volatility Smirk Tell Us About Future Equity Returns?" | *Journal of Financial and Quantitative Analysis* 45(3), 641–662 | https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/what-does-the-individual-option-volatility-smirk-tell-us-about-future-equity-returns/ECFD16BA9ACBDC8D577D1BD866FBEA72 | 2010 | 2026-07-24 | C4 economic rationale | Steeper individual-equity volatility smirks predict lower future equity returns; consistent with informed traders with negative news preferring OTM puts, and the equity market being slow to incorporate that information | **Official-source, higher confidence** — corroborated across Cambridge Core, SSRN, and multiple secondary academic sources. |
| 13 | McLean, R.D.; Pontiff, J., "Does Academic Research Destroy Stock Return Predictability?" | *Journal of Finance* 71(1), 5–32 | https://onlinelibrary.wiley.com/doi/10.1111/jofi.12365 | 2016 | 2026-07-24 | C3 (and general) overfitting/leakage-risk framing | Portfolio returns on 97 published cross-sectional predictors are 26% lower out-of-sample and 58% lower post-publication on average, consistent with published-effect decay from informed trading | **Official-source, higher confidence** — corroborated across Wiley, SSRN, RePEc, and multiple secondary sources. |
| 14 | `config.py` | This repo | `/Users/carsynstephenson/options-validator/config.py` | N/A (current HEAD at task time) | 2026-07-24 | Orthogonality checks for all five candidates; universe/scope facts | Full file read directly. No volume, OI-change, put/call-ratio, or skew constant exists anywhere. `MIN_OPEN_INTEREST`/`MAX_SPREAD_PCT` are option-leg liquidity fields only. `H5_VRP_SELL_GREEN`/`iv_minus_rv` is the nearest conceptual (not code-level) neighbor. `ATTRACTIVENESS_UNIVERSE` is a 14/15-name AI-infrastructure-thesis board, not a broad cross-section. | **Repo-verified** — direct file read, this session. |
| 15 | `options_researcher/attractiveness.py` | This repo | `/Users/carsynstephenson/options-validator/options_researcher/attractiveness.py` | N/A | 2026-07-24 | Orthogonality and implementation-fit checks | Full file read directly. `put_card_rows`/`cc_card_rows`/`pmcc_card_rows` already read `iv`, `delta`, `strike`, `open_interest` per contract; `ladder_cards()` shows the repo's existing pattern for adding a new per-bucket badge without touching the frozen ranking recipe. | **Repo-verified** — direct file read, this session. |
| 16 | `data/thetadata_adapter.py` | This repo | `/Users/carsynstephenson/options-validator/data/thetadata_adapter.py` | N/A | 2026-07-24 | Free-live-data-availability scoring for C2, C3, C4; the OI look-ahead-free design claim | Full file read directly. `CHAIN_COLUMNS` has no volume field. `_fetch_raw` calls only `option_history_greeks_eod` and `option_history_open_interest`. Comment (lines 14-17): OI reflects the prior day's ~06:30 ET OPRA report and "is already known during day D, so joining day-D OI is look-ahead-free." | **Repo-verified** — direct file read, this session. |
| 17 | `options_researcher/live_quotes.py` | This repo | `/Users/carsynstephenson/options-validator/options_researcher/live_quotes.py` | N/A | 2026-07-24 | Live-entitlement facts for C2/C3 | Full file read (relevant sections) directly. `REQUIRED_PROBE_ENDPOINTS = ("option_list_expirations", "option_snapshot_quote", "option_snapshot_greeks_all", "option_snapshot_open_interest")`; a stock-entitlement denial falls back to put-call-parity spot for trigger names only, per the module's own docstring. | **Repo-verified** — direct file read, this session. |
| 18 | Installed `thetadata` Python client | Local `.venv` install, this repo | `/Users/carsynstephenson/options-validator/.venv/lib/python3.12/site-packages/thetadata/client.py` | Installed version, this environment | 2026-07-24 | C3 data-feasibility note (volume endpoint exists in the client but is unused/unconfirmed) | `grep` of the installed client shows real `option_history_trade`, `option_snapshot_trade`, `option_history_ohlc`, and `option_snapshot_ohlc` method definitions, none of which are called anywhere in this repo's `data/thetadata_adapter.py` or `options_researcher/live_quotes.py`. | **Repo-verified** that these methods exist in the installed client and are unused in this repo; **Assumption** that this account's specific entitlement tier would actually authorize a live call to them (untested; this repo's own memory record notes other non-quote endpoints have been denied before). |
| 19 | `docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md` | This repo | `/Users/carsynstephenson/options-validator/docs/superpowers/plans/2026-07-22-rq2-scanner-enrichment-briefs.md` | 2026-07-22 (session file) | 2026-07-24 | Orthogonality checks against the already-committed RQ2 badges (B1, A1, C1, N3-1, V1, H1) | Full file read directly. B1 is specifically a near-vs-far TENOR slope (`ts_slope = atm_iv_near − atm_iv_long`) at fixed moneyness, distinct from C4's strike-dimension skew slope at fixed tenor. | **Repo-verified** — direct file read, this session. |
| 20 | QuantConnect research index page | QuantConnect.com | https://www.quantconnect.com/research/ | N/A | 2026-07-24 | Attempted independent verification of row 1; informs the confidence caveat on row 1 | Direct fetch returned "No Results" / "TOP 5 Research Publications" with a dash and "Loading..." placeholders — no article listing rendered | **Repo/tool-verified fact about what this fetch returned**; this by itself does NOT prove row 1's page is fake (the sibling file's independent author/paper cross-check, row 2, argues the opposite) — recorded as an inconclusive check, not treated as disqualifying. |

**Unresolved evidence gaps, carried forward honestly:**

- The QuantConnect target page's exact numeric backtest figures (Sharpe
  ~0.792 vs ~0.406) and its named "Spectral Tick-Flow Signal" dataset/field
  names (`volume_variance_explained`, `execution_score`) could not be
  independently corroborated against a second source by either this file or
  its sibling `.research/01_periodicity.md`; a direct SSRN fetch of the
  underlying methodology paper (Wu, Zhang & Dai) returned HTTP 403. Per the
  task's own selection rule, this is not load-bearing for the lead
  selection, which argues from mechanism and feasibility instead.
- Whether this repo's actual ThetaData account entitlement would authorize a
  live call to `option_snapshot_trade` (needed for a true, volume-based
  put/call ratio, C3) is unverified — flagged as an Assumption, not tested
  here (this file made no live ThetaData calls, per its read-only/no-Bash-
  execution scope for anything beyond local repo/package inspection).
- Whether this repo's live-side `option_snapshot_open_interest` request
  (used by C2's live path) actually succeeds against the current account
  entitlement, versus being requested-but-denied like some other non-quote
  endpoints this repo's own memory records, was not independently
  re-tested in this session.
