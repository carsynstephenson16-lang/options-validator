# Composite-signal lane: delivery decision, status rulings, and design

**Date:** 2026-08-04 (session started 2026-08-03)
**Authority:** owner-directed in-session 2026-08-03 (ship-blocker retired; composite-indicator
work commissioned; delivery form delegated — see `.cursorrules` amendment of same date).
**Provenance:** rulings and design below are agent-decided under that delegation,
labeled LLM-asserted where numeric; owner retains veto by append-only amendment.

---

## Part 1 — Rulings on the five open status items

### 1.1 Which hypotheses can still reach a verdict

Facts (repo-verified via ledger/README extraction, 2026-08-03):

| Hypothesis | Positions | Window end | Loss bar | Data dependency |
|---|---|---|---|---|
| H5 (LEAPS entry watch) | 0 fires | none (alert lane) | n/a | exact-session cache; fail-closed |
| H6 (post-earnings calls) | 1 open, 0 closed | none | 3 full-loss months | marks need current chains |
| H7 (forward window) | 0 | PAUSED (OD-3: do not restart) | 10 | dead (provider ended) |
| H8 (pre-earnings) | 0 | none | CI90 after 8 completed | current chains |
| H10a | 0 | 2026-10-06 | 7 | live chain snapshots |
| H10b | 0 | 2027-01-06 | 7 | live chain snapshots |

**Ruling:** do **not** loosen any registered entry condition mid-window. Loosening
after observing zero fires is conditioning on the data — the exact practice the
2026-07-24 feasibility gate was written to prevent, and the gate's own diagnosis
is that these stacks were registered too tight (H10b pre-disclosed only 11
historical fires). With the canonical chain cache frozen at 2026-07-27 (OD-4),
no forward hypothesis can accumulate marks regardless of thresholds. Therefore:
let H8/H10a/H10b run to their declared ends and record `INSUFFICIENT_SAMPLE`
honestly — in this repo that is a legitimate, success-grade outcome, not a
failure. H6's single open position adjudicates on its own registered terms. H7
stays paused per OD-3. The verdict-bearing successor is a **new registration
built on the composite-signal lane's observed base rates** (Part 3), designed
from the start to pass the feasibility gate (expected entries ≥ 2× loss bar) —
i.e., designed to actually fire.

### 1.2 The data problem (gates everything forward-looking)

Facts: commercial ThetaData access ended 2026-08-01 (OD-4); acquisition is
technically disabled (Q7); the Schwab lane is read-only live quotes + a 13:00
display recorder with **no dated-historical-chain endpoint**; canonical cache
edge 2026-07-27.

**Ruling:** two honest paths, and only the owner can choose the second:
(a) **Frozen-cache research mode (default, active now):** the composite lane
runs entirely on cached chains + cached closes, fully labeled with as-of
stamps. Research continues; no forward verdict accumulates. Zero spend.
(b) **New provider lane (owner-only decision, spend):** if a forward verdict
before H10a's 2026-10-06 close matters, a replacement EOD-chain source must be
authorized. That is a spend decision this agent cannot and will not make
(operating-manual rule: data-provider decisions are deferred until the phase
that needs them — that phase has now arrived; verify integration before paying).
This report deliberately makes (a) productive so (b) is a choice, not an
emergency.

### 1.3 The four entry-banned names (AVGO, CRWV, IREN, USAR)

Fact: banned per-name by the fail-closed `EARNINGS-UNKNOWN` gate (no earnings
provenance rows), inside a hypothesis that is itself paused. A manual cure path
exists (`tools/h7_refresh_earnings.py` with confirmed dates).

**Ruling:** spend no effort curing entry bans for a paused lane — that is dead
work. The bans are operationally moot. The composite lane (display-only)
shows every cached name with a **data-health badge** instead of an entry ban —
display needs honesty labels, not entry gates. If an H7-successor is ever
registered, cure earnings provenance then, as part of its restart contract.

### 1.4 RQ2-v1 and A2-v1 (registered 2026-07-23, never run)

Facts: their registered forward window has not opened (RQ2 starts 2026-09-01,
12-month backstops); they are offline/cache-only by design; they are blocked by
three unbuilt badge modules (B1 term-structure corner, A1 bounce lens, V1
VRP-calibration) plus rates/dividend CSV unlocks — not by any provider.

**Ruling: RETAIN, do not retire.** "Registered and never run" is not a breach
here — the window hasn't opened. Retiring a timely, offline-runnable registered
design would destroy value. Synergy note: the composite lane's vol-premium and
term-structure computations (Part 3, Angle 2) are built as reusable modules so
the RQ2 badge builds can consume them — one build serves both programs.

### 1.5 Housekeeping

- **Origin branch cleanup: EXECUTED 2026-08-04.** 24 stale branches deleted
  from `origin` (19 verified fully merged into `origin/main`; 5 unmerged but
  verified present locally AND pinned by `archive/2026-08-03/*` tags already
  pushed to origin; zero open PRs). Origin now holds exactly `main` and
  `sfix`. Preservation verified before deletion; `irreplaceable_data_guard`
  verified OK from the main checkout.
- **The 2 kept local branches** (`codex/h7-stage8-critical-20260717`,
  `codex/qm-dashboard-integration-20260717`): **KEEP, harvest-only**, per the
  disposition doc. The qm branch's two fail-closed display guards are harvested
  as *concepts* into this lane's design (freshness fail-closed rendering); the
  h7 branch's 16 validator functions await any future H7-successor
  registration. Neither branch merges.
- **`settings.local.json` ff-only permission:** ruling is REMOVE (the merge it
  served is done; leaving it grants standing merge authority in the ops
  worktree). The automated config-safety classifier blocks this agent from
  editing that file this session, so this is a one-line owner action: delete
  the line `"Bash(git -C /Users/carsynstephenson/options-validator-ops merge --ff-only:*)"`
  from `.claude/settings.local.json` (main checkout and worktree copy).
- **Guard footgun observed:** `irreplaceable_data_guard.py verify` reports
  false MISSING-ENTIRELY for every cache when run from a worktree (worktrees
  have no `.cache/`). Run it from the main checkout; a cwd-anchor fix is a
  candidate follow-up.
- **README "Scope status" is stale:** it lists only H5–H8 and omits H10a/H10b,
  RQ1 (spent), RQ2-v1, A2-v1. Follow-up doc-truth repair recommended (Q1-style,
  docs-only).

---

## Part 2 — Delivery-form decision (delegated; recorded per amendment)

**Decision: a new display-only lane inside this repository, surfaced alongside
the attractiveness dashboard. Not a new repository.**

Reasoning (each point evidence-backed):
1. Every input the lane needs already lives here behind tested guardrails: the
   31,366-file manifest-bound chain cache, `data/underlying_closes.py`, and the
   walk-forward regime module `options_researcher/regime.py` (built, tested,
   and one-run verified non-redundant: REGIME-AMI-v1 median AMI 0.0295 vs 0.50
   threshold → RETAINS_DISTINCT_INFORMATION, receipt 2026-08-03).
2. A separate repo would duplicate data plumbing, escape the hooks
   (live-trading blocker, ledger guard), and restart test/CI infrastructure
   from zero — pure plumbing tax, no research payoff.
3. Precedent: the Wasserstein lane was authorized 2026-08-03 exactly this way
   (in-repo, display-only, cached-data-only) and shipped cleanly under it.
4. The owner's stated goal is one decision view combining several angles —
   which is a dashboard-integration problem, i.e., strongest inside the repo
   that owns the dashboard.

Constraints inherited (agent-proposed, binding pending owner veto): cached data
only (OD-4 stands), causal walk-forward computation only, max as-of session on
every output, display-only — not verdict-bearing, not FIRE-capable, and no
registered signal without a future registration passing the feasibility gate.

---

## Part 3 — The composite: four angles, one card

Four angles (within the owner's 3–6 band). Design principle: each angle answers
a **different question**, so they compose as orthogonal axes on one card rather
than competing estimates averaged into mush — no angle can "diminish" another,
which is the owner's stated requirement and matches the forecast-combination
literature's core warning (estimated optimal weights lose to simple structure:
Clemen 1989; Timmermann 2006; DeMiguel-Garlappi-Uppal 2009).

**Angle 1 — TREND (question: which direction, if any?).**
Two EMAs on cached closes: slow research-baseline EMA-200d and medium EMA-50d
(owner's requested pair-structure), plus the sign of the 12-month-minus-1-month
return (time-series momentum). States: UP / DOWN / MIXED.
Parameters are standard-from-literature and frozen — deliberately NOT tuned:
Levine & Pedersen (2016, FAJ 72(3)) show EMA crossovers and time-series
momentum are near-equivalent linear filters with performance roughly flat
across speeds (secondary-source-verified; flagged), so speed choice matters
less than implementation honesty; Man AHL discloses blending multiple EWMA
speeds rather than optimizing one (official-source). TSMOM 12-1 anchor:
Moskowitz, Ooi & Pedersen (2012, JFE 104(2)). Caveats displayed: Lo, Mamaysky
& Wang (2000) found technical signal weakest in the most liquid names
(MSFT/AMZN caveat); Sullivan, Timmermann & White (1999) — even
snooping-corrected winners decayed out of sample.

**Angle 2 — VOLATILITY PREMIUM (question: is optionality rich or cheap?).**
Headline construct: **IVRV gap** = 30d ATM implied vol (interpolated from
cached chain) minus 20d realized vol (closes). Secondary: IV term-structure
slope (near vs far ATM IV). Display context: existing IV percentile (kept as
context only — IV rank alone has no direct peer-reviewed support; the *gap* is
the validated construct: Goyal & Saretto 2009, JFE 94(2) — IV−HV sorted
straddles ~22%/mo gross shrinking to ~3.9%/mo after full quoted spreads, the
honest cost-shrinkage benchmark). Slope direction: Vasquez (2017, JFQA 52(6)).
Single-name caveat displayed prominently: the short-vol premium is weaker,
noisier, possibly absent in single names vs index (Bakshi & Kapadia 2003 RFS
16(2) + 2003 J. Derivatives; Carr & Wu 2009 RFS 22(3); Driessen, Maenhout &
Vilkov 2009 — priced correlation risk explains the index/single-name gap).
High-idio-vol names (VST/CEG) show *larger* gross premia explained by
intermediation frictions — costs plausibly eat it (Cao & Han 2013 JFE 108(2);
Boyer & Vorkink 2014 JF 69(4)). States: RICH / CHEAP / NEUTRAL → structure
preference (credit-side vs debit-side), never an entry command.

**Angle 3 — REGIME (question: what kind of market is this, historically?).**
The existing walk-forward Wasserstein k-means labels (`options_researcher/
regime.py`) — method: Horvath, Issa & Muguruza (2021, arXiv:2110.11848; J.
Computational Finance 28(1)) — with the repo's own AMI receipt showing the
labels carry information distinct from a realized-vol percentile. Regime
renders as context + a *descriptive* size band (vol-targeting helps risk
assets: Harvey, Hoyle, Korgaonkar, Rattray, Sargaison & van Hemert 2018, JPM
45(1); displayed alongside the implementability critique: Cederburg, O'Doherty,
Wang & Yan 2020, JFE 138(1)). Honesty constraint from the causal-labeling
literature: real-time labels transition ~2× as often as hindsight labels (Shu
& Mulvey 2024, arXiv:2410.14841) — so regime is a **context layer, not a
switch**, and boundary flicker is expected and shown, not smoothed away.
Gate-vs-continuous is unresolved in the literature (flagged honestly) — another
reason regime stays descriptive here.

**Angle 4 — OPTIONS-MARKET INTERNALS (question: does the options market
corroborate?).**
(i) The ratified OI-change line v1 (shipped 2026-07-25) — EOD-native
open-interest change; peer-reviewed support for OI-change predictiveness:
Fodor, Krieger & Doran (2011, FMPM 25(3)). (ii) 25Δ skew/smirk level vs its
own trailing history — steep smirk is a documented *bearish* signal for the
underlying (Xing, Zhang & Zhao 2010, JFQA 45(3): ~10.9%/yr risk-adjusted
spread, persists months, computable from EOD chains). (iii) Liquidity health
badges from the existing MIN_OPEN_INTEREST / MAX_SPREAD_PCT gates. States:
CONFIRM / NEUTRAL / VETO. (Pan & Poteshman 2006's stronger volume signal needs
buy-to-open classification that EOD data cannot provide — explicitly out of
scope, recorded so nobody "approximates" it dishonestly.)

**Composition — the confluence card.** Per name, per session: the four angle
states render side-by-side plus a confluence grade = count of non-neutral
angles aligned with the trend direction (A: 3–4 aligned, B: 2, C: otherwise;
VETO from Angle 4 caps the grade at C). Lexicographic and countable — the same
pattern as attractiveness v2's GREEN-fraction ranking — never a weighted sum
(equal-structure beats estimated weights: Clemen 1989; DeMiguel et al 2009).
Every card carries its max as-of session; any angle whose inputs are missing
or stale renders DATA_BLOCKED (fail-visible), harvesting the two fail-closed
display-guard concepts from the kept qm-dashboard branch.

**Anti-overfitting discipline (binding on this lane):** zero per-name
parameter tuning; every constant standard-from-literature, frozen in
`config.py` with an LLM-proposed provenance comment; walk-forward computation
only; no backtest-derived claims from this lane (vocabulary discipline
applies); any future registered use must pass the deflated-Sharpe / PBO
machinery already in `options_researcher/robustness` (Bailey & López de Prado
2014, JPM 40(5); Bailey, Borwein, López de Prado & Zhu 2017, J. Comp. Finance
20(4)) and the t>3 multiple-testing hurdle discussion (Harvey, Liu & Zhu 2016,
RFS 29(1); contested down to ~1.8 by Chen & Zimmermann — both sides cited).

**Why exactly four:** the owner's band is 3–6 with a warning that indicator
stacks overfit. Four is the count of genuinely distinct questions the cached
data can answer (direction / price-of-optionality / environment /
corroboration). A fifth angle from the same data (e.g., raw IV rank entries,
volume periodicity) would either restate Angle 2 or resurrect an idea already
rejected by this repo's own ledger (volume-periodicity REJECTED 2026-07-25).

---

## Part 4 — Source index (compressed)

Full verification notes with URLs live in `.tmp/agent-briefs/` (three files,
gitignored scratch); citations above give author-year-venue sufficient for
recovery. Items flagged as secondary-source-verified: Levine-Pedersen Table-1
specifics; Carr-Wu single-name sign. Items with digit-level verification
failures (direction confirmed, magnitude paywalled): Vasquez 2017 spread;
Eraker-Johannes-Polson κ. Dubinsky-Johannes earnings-IV is an unpublished
working paper — the peer-reviewed originators are Patell & Wolfson (1979,
1981). Jane Street publishes no alpha methodology (it is primarily a
market-maker/ETF-AP arbitrageur); AQR and Man AHL are the reusable
published-practice sources.
