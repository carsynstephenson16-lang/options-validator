# Options Scanner & Research Platform — VST · CEG · MSFT · AMZN

## Schwab live market data

The live-preview lane supports read-only Schwab quotes and option chains.
Historical caches, backtests, scoring, positions, receipts, and official
verdicts remain unchanged. Setup uses one hidden macOS Keychain prompt:

```bash
uv run python tools/setup_schwab.py
```

See [docs/schwab-market-data-setup.md](docs/schwab-market-data-setup.md) for
the short first-time authorization process and security boundaries.

**Mission (owner decision 2026-07-03; clarified 2026-07-06):** research how
the options of four AI-infrastructure names — Vistra (VST) and Constellation
(CEG) on the nuclear/data-center power side, Microsoft (MSFT) and Amazon
(AMZN) on the Mag-7 cloud side — actually behave, then scan for contracts
that look attractive enough to consider. **Scanner first. Research only.
This is NOT a live bot and places no orders.** A candidate becomes a tracked
position only after the owner intentionally adds it to `data/positions/`.
"No edge after costs" is a successful finding — the point is to learn that
cheaply, before risking money.

The platform has two layers, and the separation is deliberate:

1. **The discipline layer** (kept from the project's first phase, fully
   tested): conservative fill model (quote mid **or worse**, commissions both
   legs both ways, adverse haircut), liquidity gates on every leg, a
   scoreboard whose verdict gates on the number of **losses** (not trades),
   dependence-aware confidence intervals, an append-only research ledger, and
   a sealed-holdout protocol. This layer exists because it already caught
   three tempting strategies (H1, H2, H3-draft) that would have lost money.
2. **The research layer** (`options_researcher/`, new): descriptive studies
   and scanner views for the four names' options — liquidity, strike grids,
   implied-vol behavior, how option prices react around big moves — that
   produce *facts first*, then candidate cards, and only later tracked
   positions or pre-registered strategy tests.

## Current status

`PROJECT_STATE.md` is the canonical status and execution queue. Older roadmap
documents remain historical evidence; they do not override its gates or task
ordering.

| Piece | State |
|---|---|
| Universe | `config.UNIVERSE = ["MSFT", "AMZN", "VST", "CEG"]` |
| Chain data | The verified canonical inventory contains 31,366 top-level daily EOD files, 79,519,407 rows, and 26 symbols. MSFT/AMZN/VST end on 2026-07-27 (2,152 sessions each); CEG covers 2022-02-09 through 2026-07-27 (1,118 sessions). All 33 July 24/27 additions are now manifested. One nested SPY snapshot is preserved but explicitly noncanonical. |
| Tradability profile | `options_researcher/profile_tradability.py` — first findings below |
| Backtest path | Offline Lumibot/PandasData harness + `tools/score_backtest.py` scoreboard CLI, wired against the real cache |
| Feasibility | `analysis/feasibility.py` — credits measured from cached chains, not assumed |
| Current holdings | `data/positions/holdings.csv` records 39 VST shares. The legacy `positions.csv` and H8 book are empty; the H6 paper book has one open NVDA call (`H6-0001`) and zero completed positions. |
| Scanner mode | `options_researcher.attractiveness` and `options_researcher.attractiveness_dashboard` show candidates; they never add trades or mutate positions. |
| Discipline layer | Full unittest suite green (`uv run python -m unittest discover -s tests`; exit code is the verdict — don't trust a hardcoded count) |
| Strategy history | H1 ($2-wide SPY/QQQ put spread), H2 ($5-wide): registered, honest in-sample **FAILs**. H3R (SPY conditional-VRP): archived un-run at scope pivot. Ledger records are permanent; OOS budget 0/3 spent |

### What the early profile said (sampled days, ~37-DTE puts)

- **MSFT**: tradable under our gates since 2019; spreads ~3–9%; $5 strike
  grid since 2021. Best-behaved name of the four.
- **AMZN**: thin before its 2022 split, good after — spreads ~2–4%, growing
  open interest, 6–12 strikes passing gates recently.
- **VST**: rich implied vol (50%+ in 2024–25) but **ATM open interest failed
  our ≥100 floor in every sampled year, including 2024–26**. Caveat: weekly
  expirations may fragment OI; checking monthly expiries is a roadmap item.
  Until then, VST structures must assume poor fills.
- **CEG**: fetched 2026-07-04, and it rhymes with VST — rich implied vol
  (45–53% in 2024–26) but thin ATM open interest at the sampled ~37-DTE
  expiries: passed our gates in 2023 (7.7% spread, OI 134), just missed in
  2024 (OI 87), collapsed at sampled expiries in 2025–26. Only ~4.5 years of
  option history exist at all. The monthly-expiry check decides CEG too.

Later correction: the monthly-expiry check below changed the VST/CEG picture.
For scanner purposes, monthly expirations are the default target.

## Quickstart

Python 3.12 managed by uv; the lockfile is the source of truth.

```bash
uv sync --frozen
uv run python -m unittest discover -s tests                 # discipline layer
uv run python options_researcher/profile_tradability.py     # 4-name liquidity profile
uv run python analysis/feasibility.py                       # sizing vs the sleeve
uv run python tools/score_backtest.py --symbols MSFT,AMZN --json   # in-sample scoreboard
uv run python -m options_researcher.attractiveness            # which options look attractive today
uv run python -m options_researcher.entry_watch                # WAIT/FIRE vs the frozen entry triggers
uv run python -m options_researcher.h7_watch                    # session-aligned H7 watcher; alerts only
uv run python -m options_researcher.h7_source_health           # earnings provenance alive? (exit 1 on any unhealthy name)
uv run python -m options_researcher.h7_data_gate --source-health-receipt <path>  # exact-session daily data gate; receipt required
uv run python -m options_researcher.h7_event_ledger verify     # verifies the current one-record registration store
uv run python tools/h7_refresh_earnings.py --help               # owner-run append-raw/promote refresher
uv run python data/recent_topup.py --scope h7 --dry-run         # 12-name missing-session inventory; no network
uv run python tools/thetadata_exit_audit.py --scope h7          # read-only forward-cache exit audit
uv run python -m options_researcher.portfolio                 # mark recorded options, if any
uv run python -m options_researcher.dashboard                  # writes .tmp/dashboard/index.html
uv run python -m options_researcher.attractiveness_dashboard    # interactive at-expiration scenario view (writes .tmp/dashboard/attractiveness.html)
uv run python -m options_researcher.robustness --help            # registered research-only robustness experiments
```

`smoke_test.py` probes a single in-sample chain (cached parquet, or the
official ThetaData client on a cache miss). Post-`IN_SAMPLE_END` values stay
sealed for the legacy holdout machinery unless the reveal gate opens them.

### Isolated external model checks

The root environment does not depend on third-party pricing or portfolio
libraries. Git-pinned, separate checks are documented in
`tools/third_party/README.md`:

```bash
uv run --frozen --project tools/bs_parity python tools/bs_parity/run.py
uv run --frozen --project tools/financepy_validation python tools/financepy_validation/run.py
```

`vollib` is parity-test-only. FinancePy is GPL-3.0-or-later and remains in a
separate validation environment. OpenBB is reserved for non-canonical
`equity-research` enrichment; `ffn` is deferred, and `pysabr`, `willowtree`,
and `finoptions` are reference-only.

### Reproducing a ledger record

A fresh clone canNOT re-run a logged experiment as-is; three things are
required, in order:

1. **The dependency surface**: `uv sync --frozen` (the lock is folded into
   each record's `source_hash`).
2. **The exact code**: `git checkout <code_sha>` from the ledger record —
   `config.py` drifts between hypotheses by design, and the reveal gate's
   `config_hash` check will refuse a drifted tree.
3. **The exact data**: the parquet chain cache (`.cache/chains/`, ~2.3 GB)
   is gitignored. ThetaData acquisition is disabled, so preserve or copy these
   immutable bytes rather than assuming they can be downloaded again.
   `data/chain_cache_manifest.txt` freezes its per-file sha256 —
   `uv run python tools/cache_manifest.py verify` proves a (re-fetched or
   copied) cache is byte-identical to the one the records were produced
   from. Regenerate with `... generate` only on a deliberate cache change,
   and commit the diff alongside the change that caused it.

H4/H5 forward-window entries are time-dependent paper marks, not
re-runnable point results; their "reproduction" is the positions CSVs plus
the dated reports.

## Capital & risk

`RISK_SLEEVE` ($14k) and `MAX_LOSS_PER_TRADE` ($600 economic max loss, owner
decision 2026-07-02) live in `config.py`. The current recorded state includes
one open H6 NVDA paper call and no H7/H8 option position. If the scanner later surfaces
an attractive candidate and the owner adds it, four concurrent option
positions would put about $2,400, or 17.1% of the sleeve, at simultaneous
risk — and these four names are **one AI-infrastructure cluster, not four
independent bets**; in an AI or power-sector drawdown they can lose together.
Never size against net worth, and never raise the cap to make a structure
"fit".

## Research rules (non-negotiable, inherited)

See `.cursorrules` and `AGENTS.md`. No look-ahead; fills at quote mid or
worse; commission plus half-spread on both legs; liquidity filters on both
legs; verdicts gate on losses; every strategy number lives in `config.py`;
data gaps are skipped and logged, never papered over. New strategy ideas are
**pre-registered in the ledger before results exist** — parameters frozen
first, run once, result recorded whatever it shows. The 2023+ window is no
longer a credible blind holdout for these four names (they were picked
knowing the 2023+ AI boom, and profiling has opened their recent
microstructure — disclosed in `ledger/facts.log`); future hypotheses
therefore pre-declare their own validation design, e.g. a forward
paper-trading window.

## Roadmap (one scoped step per prompt)

1. ~~**CEG data**~~ — DONE 2026-07-04: 1,100 chains cached, profiler re-run
   (see findings above; `ledger/facts.log` CEG_CACHE_COMPLETE).
2. ~~**VST + CEG monthly-expiry check**~~ — DONE 2026-07-04, and it flipped
   the picture: open interest is 85–100% concentrated in **monthly**
   expirations for all four names, and at the nearest monthly (~30 DTE) the
   2024–26 medians PASS the frozen gates on every name (VST OI 220 / 5.1%
   spread; CEG 212 / 5.5%; MSFT 3,213 / 2.6%; AMZN 6,462 / 2.1%). Rule
   adopted: every structure targets monthlies. See
   `options_researcher/profile_monthlies.py`. Remaining steps now follow
   `docs/superpowers/specs/2026-07-04-research-platform-completion-design.md`
   (M1 research core → … → M7 dashboard).
3. ~~**Behavior studies**~~ — DONE 2026-07-04 (`reports/2026-07-04-*.md`):
   (A) high IV rank did NOT mean rich premium — realized met/exceeded
   implied on all four names; (B) earnings IV run-up/crush is real on
   MSFT/AMZN only; (C) monthly 0.20Δ covered calls ≈ buy-and-hold on AMZN
   (+$8/47 cycles) but gave up $3.3k/42 cycles on VST's bull run.
4. ~~**Structure menu**~~ — DELIVERED 2026-07-04, awaiting owner picks:
   `docs/superpowers/2026-07-04-structure-menu.md` (recommended H4: AMZN
   monthly 0.20Δ covered call; close-data Option A/B decision bundled).
5. ~~**First 4-name hypothesis (H4)**~~ — FROZEN 2026-07-04, then superseded
   by H5 before any completed cycles. The old seeded rows were not the
   owner's real current positions and have been cleared. Current mode:
   scanner first; add a row to `data/positions/positions.csv` only after a
   candidate is attractive enough to track intentionally.
6. **Composite evidence backtest** — DONE 2026-07-04:
   `uv run python -m options_researcher.h4_backtest` replays the old H4
   recipe (2023-01..2026-06: combined +$14.7k, 9/14 quarters positive, worst
   quarter −$5.1k). This is historical evidence only, not the current book and
   never the verdict.
7. ~~**Dashboard (M7)**~~ — DONE 2026-07-04:
   `uv run python -m options_researcher.dashboard` writes a self-contained
   `.tmp/dashboard/index.html` (dark, game-styled, no network/JS deps) —
   watch cards per name, any recorded options, quest log, and an achievement
   wall built from `ledger/facts.log`.
8. ~~**Attractiveness scenario view**~~ — DONE 2026-07-06:
   `uv run python -m options_researcher.attractiveness_dashboard` writes a
   self-contained `.tmp/dashboard/attractiveness.html` over the same
   candidates the `attractiveness` CLI prints. Each candidate gets a
   plain-language "if the stock is at price X, your gain or loss is Y" table
   priced **at expiration** (intrinsic value only — no options-pricing
   model). PMCC rows only appear after a real LEAPS is recorded in
   `positions.csv`; covered-call rows only appear after a declared 100-share
   lot. Reuses the M7 CSS; no network/JS deps.

**Scope status: four live hypotheses, forward paper windows.**
**H5 Sector Income Core scanner/researcher**
(`docs/superpowers/specs/2026-07-04-h5-sector-income-core-design.md`; ledger
trial 6; H4 superseded at zero cycles) and **H6 post-earnings tactical long
calls** (ledger trial 7, registered 2026-07-08; NVDA/PLTR/AMZN; ≤$2k
premium/month; design + screen evidence in
`docs/superpowers/2026-07-08-h6-monthly-income-candidate-memo-DRAFT.md`).
H6 now has a dedicated read-only, forward-paper evaluator; it does not reuse
the generic H4 tactical preview and has no live-order path. Build exact-session
IV-rank artifacts from the audited local cache, then run the watch:

```bash
uv run python -m options_researcher.h6_features --as-of YYYY-MM-DD
uv run python -m options_researcher.h6_watch --as-of YYYY-MM-DD --json
uv run python -m options_researcher.h6_watch --as-of YYYY-MM-DD \
  --write-receipt reports/h6_forward/YYYY-MM-DD.json --json
uv run python -m options_researcher.h6_watch --as-of YYYY-MM-DD \
  --verify-receipt reports/h6_forward/YYYY-MM-DD.json --json
```

The watch reads point-in-time earnings assertions from `gating_v3.csv`, the
exact-session cached chain, and the manually maintained
`data/positions/h6_positions.csv`; missing/stale facts block rather than fall
back. The feature builder atomically writes one self-hashed manifest beside
each parquet artifact. Each manifest binds every contributing chain, the raw
close store, the exact output bytes, feature constants, runtime versions, and
builder source. Every chain must also match its timestamped, content-bound
`BLIND_CACHE` acquisition fact; a missing/malformed fact or SHA mismatch stops
the build/watch. The watch refuses missing, stale, or mutated manifests. A
clean watch can then create one immutable receipt binding those manifests and
outputs to the trial-7 registration, full book, raw/promoted earnings stores,
exact-session chains, frozen H6/cost/bootstrap parameters, and evaluator
source. Verification fully recomputes that receipt; any changed surface
invalidates it. A receipt proves what the read-only watch saw, not that a paper
entry was recorded prospectively. Every future book entry and close must cite
its exact receipt SHA-256. One receipt may authorize only one manual book
action; after recording that action, rerun the watch under a new filename
before recording another. This makes portfolio risk cumulative rather than
letting several same-snapshot candidates spend the cap independently. Keep
action receipts under `reports/h6_forward/`, the default verification
directory. NVDA's 2021/2024 split entries are already in the closes registry.
The book holds one open position (H6-0001: NVDA $220 call, exp 2026-09-18,
1 contract, entered 2026-07-13 at $920.65 premium, receipt-bound in
`data/positions/h6_positions.csv`) and zero completed positions, so H6
remains `INSUFFICIENT_SAMPLE`; no result or edge is claimed.
**H8 pre-earnings tactical long calls** (ledger trial intent `1eed4ae6`,
registered 2026-07-15; companion to H6, forward-paper only; all frozen
numbers were LLM-decided under explicit owner delegation, disclosed in the
registration entry): PLTR and AMZN only — NVDA excluded because the E1
descriptive study measured ~0 pre-event IV run-up there. Structure: single
long call, nearest standard monthly 45–90 DTE, highest delta in 0.30–0.50,
ask ≤ $1,000, both-leg liquidity gates. Entries are allowed ONLY T-15..T-8
XNYS sessions before a company-CONFIRMED report date (estimated/aggregator
dates fail closed) AND IV-rank ≤ 0.50 at entry; hard close at T-2 sessions
before the report, take-profit +75%, no stop-loss. The monthly
premium-at-risk cap is SHARED with H6 (combined ≤ $2k/month), max 1 contract
per name, max 2 concurrent, and H8 never opens on the same underlying as an
open H6 position. Read-only watcher (mirrors h6_watch; alerts only, never
writes the book): `uv run python -m options_researcher.h8_watch`. The paper
book `data/positions/h8_positions.csv` is header-only. First board
(evaluation session 2026-07-14, fact H8_FIRST_BOARD): PLTR window OPEN but
blocked by the IVR gate (0.81 > 0.50); AMZN blocked fail-closed
(2026-07-30 still aggregator-estimated). Verdict gates on completed
positions (bootstrap CI90 after 8 completed; hard kill on 3 consecutive
full-cap loss months); with zero completed positions H8 is
`INSUFFICIENT_SAMPLE`.
**H7 swing options on volatile AI names** (ledger trial 8, registered
2026-07-09, `f1887c9d` + amendments v1.1–v1.7; owner scope override
2026-07-09): three separately-judged lanes on CRWV/TEM/PLTR/NOW/SMCI/NVDA/
AMD/AVGO/IREN/USAR (+ core names, long lanes only; IREN and USAR were added
by owner-typed amendments v1.5/v1.6 and activated 2026-07-15 after their
option-chain backfills — see `config.H7_WATCHLIST` and the ACTIVATION facts
in `ledger/facts.log`). Daily screen:
`uv run python -m options_researcher.h7_watch` (session-aligned, executes
the registered decide functions, fails closed on unknown earnings or book
errors). **Repo-verified finding:** the 2018–2026 historical diagnostic is
PERMANENTLY WITHDRAWN as verdict-capable evidence (amendment v1.3,
2026-07-11): historical earnings provenance cannot be causally reconstructed.
The point-in-time forward paper window is H7's sole verdict-bearing path. The
2026-07-11 forward roadmap is historical build evidence; `PROJECT_STATE.md`
now governs sequencing, provider/cache identity, namespace choice, and any
future activation. Roadmap Stage 1 is built (2026-07-11):
`options_researcher.h7_source_health` reports per-name earnings-provenance
health over the v3 gating store, and `tools/h7_refresh_earnings.py` is the
owner-in-the-loop append-only refresher (append-raw + promote under the
7b-2R.2 citation contract). Roadmap Stage 2 is **BUILT (2026-07-12,
build-only) but NOT operationally authorized**: `options_researcher.h7_data_gate`
is a read-only whole-universe daily data gate (GO only when every name in the
live watch universe — 14 names since the IREN/USAR activations of
2026-07-15 — has an exact-evaluation-session adjusted close AND EOD chain;
exit 0 GO / 1 NO_GO / 2 invalid-or-unreadable). Its first whole-universe GO
is recorded for evaluation session 2026-07-10 (12/12 on the then-12-name
universe, `reports/h7_data_gate/2026-07-10.json`) after the authorized cache
top-up; the latest is 14/14 GO for evaluation session 2026-07-15
(`reports/h7_data_gate/2026-07-15.json`). This is data-readiness evidence,
not operational authorization.
The network-free cutoff preflight
`uv run python tools/thetadata_cutoff_preflight.py --cutoff 2026-07-29`
derives the July 28 terminal session and combines the 12-name inventory,
cache provenance, exit audit, Stage-2 gate, source health, H6 input history,
clean source identity, and real-ledger verification. It never fetches, writes,
opens Stage 8, or authorizes the paid pull; follow its status contract in the
ThetaData cancellation checklist.
Operator order (**amendment v1.4, owner decision 2026-07-14**): run and
record **source health**, then the **data gate must be exit 0 (whole-universe
GO — currently 14/14)**,
then the **watcher** may run; names whose earnings provenance is unhealthy at
the evaluation cutoff are entry-banned per-name by the watcher's registered
fail-closed gate (`EARNINGS-UNKNOWN` → no entry) and reported with the run —
they no longer block the whole board. A data-gate NO_GO still blocks the run
entirely. Aggregator-estimated dates remain non-promotable
(`docs/superpowers/plans/2026-07-14-h7-amendment-v1.4-per-name-source-health.md`).
Stages 3–7 are **BUILT but INACTIVE**. The H7 event store contains one
`window_registration` event and no paper observation, fill, or result; that
registration does not open Stage 8 or authorize entry. Stages 4–7 remain
BUILD-ONLY and SYNTHETIC-ONLY, and any future namespace or activation stays
owner-gated under `PROJECT_STATE.md`. Audit receipts v1–v4
under `reports/h7_audit/` are preserved historical BLOCK artifacts; v4 was
valid at its 7b-2R.2 source commit and is intentionally not regenerated after
forward-roadmap source/config changes. A frozen retirement gate
(`config.H7_HISTORICAL_WITHDRAWAL_HASH`) makes every historical-diagnostic
entry point refuse before reading market data.
Current recorded holdings: 39 VST shares plus one open H6 NVDA paper call; H7
has no paper position or result. Remaining for H7:
restore Stage 1 source health across the full 14-name watch universe,
confirm paid daily EOD continuity,
supply the owner-frozen window inputs, bind a clean code/config identity, then
let owner + independent review decide
whether to open Stage 8. No tracked option by itself starts the H7 window.
LEAPS entry triggers are pre-registered (2026-07-07 ledger
H5_ENTRY_TRIGGER_PREREG, VST superseded by the owner-directed forward-only
H5_ENTRY_TRIGGER_AMENDMENT_V2 of 2026-07-15): evaluate only when close ≤
trigger (VST $160 v2 — pre-amendment signal history under $140 is stale,
AMZN $220) AND IV-rank ≤ 0.5 AND the LEAPS passes the liquidity gates —
`options_researcher.entry_watch` prints the live WAIT/FIRE status. The
ThetaData acquisition is disabled. Existing cache reads remain available, but
missing data must fail closed; see `docs/provider-transition.md` and
`PROJECT_STATE.md`.

## Known limitations

- **EOD data** is an upper bound on realism — real fills happen intraday.
- **Assignment/early exercise** are not simulated (American-style, physically
  settled); defined-risk caps bound the damage.
- **Earnings gaps**: single names gap through levels at EOD cadence; any
  strategy test must handle earnings explicitly (blackouts or measured
  exposure).
- **History asymmetry**: CEG effectively starts 2022; VST's tradable era is
  recent. Sample sizes will be small; the loss-gated verdict machinery exists
  precisely so thin samples read as INSUFFICIENT SAMPLE, not fake passes.
