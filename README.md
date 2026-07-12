# Options Scanner & Research Platform — VST · CEG · MSFT · AMZN

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

| Piece | State |
|---|---|
| Universe | `config.UNIVERSE = ["MSFT", "AMZN", "VST", "CEG"]` |
| Chain data | Daily EOD chains cached for the full universe: MSFT/AMZN/VST 2018-01-02..2026-06-30 (~2,134 days each), CEG 2022-02-09..2026-06-30 (1,100 days, zero empty files; the 2018–2022-02 gap is pre-listing) |
| Tradability profile | `options_researcher/profile_tradability.py` — first findings below |
| Backtest path | Offline Lumibot/PandasData harness + `tools/score_backtest.py` scoreboard CLI, wired against the real cache |
| Feasibility | `analysis/feasibility.py` — credits measured from cached chains, not assumed |
| Current holdings | `data/positions/holdings.csv` records 39 VST shares. `data/positions/positions.csv` is empty: no options are currently open or paper-tracked. |
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
uv run python -m options_researcher.portfolio                 # mark recorded options, if any
uv run python -m options_researcher.dashboard                  # writes .tmp/dashboard/index.html
uv run python -m options_researcher.attractiveness_dashboard    # interactive at-expiration scenario view (writes .tmp/dashboard/attractiveness.html)
```

`smoke_test.py` probes a single in-sample chain (cached parquet, or the
official ThetaData client on a cache miss). Post-`IN_SAMPLE_END` values stay
sealed for the legacy holdout machinery unless the reveal gate opens them.

### Reproducing a ledger record

A fresh clone canNOT re-run a logged experiment as-is; three things are
required, in order:

1. **The dependency surface**: `uv sync --frozen` (the lock is folded into
   each record's `source_hash`).
2. **The exact code**: `git checkout <code_sha>` from the ledger record —
   `config.py` drifts between hypotheses by design, and the reveal gate's
   `config_hash` check will refuse a drifted tree.
3. **The exact data**: the parquet chain cache (`.cache/chains/`, ~2.3 GB)
   is gitignored and re-fetchable only with a live ThetaData subscription.
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
decision 2026-07-02) live in `config.py`. The current recorded state has **no
open options**, so the sleeve is not committed. If the scanner later surfaces
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

**Scope status: three live hypotheses, forward paper windows.**
**H5 Sector Income Core scanner/researcher**
(`docs/superpowers/specs/2026-07-04-h5-sector-income-core-design.md`; ledger
trial 6; H4 superseded at zero cycles) and **H6 post-earnings tactical long
calls** (ledger trial 7, registered 2026-07-08; NVDA/PLTR/AMZN; ≤$2k
premium/month; design + screen evidence in
`docs/superpowers/2026-07-08-h6-monthly-income-candidate-memo-DRAFT.md`).
H6 entry evaluation still needs: NVDA/PLTR earnings CSVs (sourced), NVDA
split entries in the closes SPLITS registry, and feature builds for the
IVR gate — until then the pre-earnings lane is blocked by design (unknown
IV-rank never passes).
**H7 swing options on volatile AI names** (ledger trial 8, registered
2026-07-09, `f1887c9d` + amendments v1.1/v1.2/v1.3; owner scope override
2026-07-09): three separately-judged lanes on CRWV/TEM/PLTR/NOW/SMCI/NVDA/
AMD/AVGO (+ core names, long lanes only). Daily screen:
`uv run python -m options_researcher.h7_watch` (session-aligned, executes
the registered decide functions, fails closed on unknown earnings or book
errors). **The 2018–2026 historical diagnostic is PERMANENTLY WITHDRAWN as
verdict-capable evidence (amendment v1.3, 2026-07-11): historical earnings
provenance cannot be causally reconstructed. The point-in-time forward
paper window is H7's sole verdict-bearing path** (roadmap:
`docs/superpowers/plans/2026-07-11-h7-forward-roadmap.md`, activation gated
on independent review). Audit receipts v1/v2/v3 under `reports/h7_audit/`
are preserved historical BLOCK artifacts; a frozen retirement gate
(`config.H7_HISTORICAL_WITHDRAWAL_HASH`) makes every historical-diagnostic
entry point refuse before reading market data.
Current recorded holdings: 39 VST shares and no options. Remaining: run the
scanner, decide whether anything is attractive enough to add, then start the
forward paper window only after an actual tracked option is entered.
LEAPS entry triggers are pre-registered (owner-frozen 2026-07-07, ledger
H5_ENTRY_TRIGGER_PREREG): evaluate only when close ≤ trigger (VST $140,
AMZN $220) AND IV-rank ≤ 0.5 AND the LEAPS passes the liquidity gates —
`options_researcher.entry_watch` prints the live WAIT/FIRE status. The
ThetaData subscription cancels ~2026-07-25 per
`docs/superpowers/2026-07-07-thetadata-cancel-checklist.md`.

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
