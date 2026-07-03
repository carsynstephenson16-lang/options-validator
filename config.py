"""
config.py — all tunable parameters for the options-strategy VALIDATION HARNESS.

PURPOSE: answer one question — does a strategy have positive expectancy AFTER
realistic costs, across multiple market regimes? This is a research/validation
tool. It is NOT a live bot and it does not place orders.

Every value here is meant to be swapped. Nothing in the strategy logic should
contain a hardcoded number that isn't sourced from this file.
"""

# ---------------------------------------------------------------------------
# CAPITAL & RISK
# ---------------------------------------------------------------------------
# IMPORTANT (read before changing): "capital" in a backtest is a STUDY KNOB,
# not your bank balance. The honest way to size risk is to decide how much of
# YOUR money is the "options book" (the risk sleeve) and cap each trade's
# ECONOMIC max loss at an explicit dollar figure decided against that sleeve --
# never against your whole net worth (which silently puts your stock portfolio
# behind every options trade) and never an arbitrary round number.
# Set RISK_SLEEVE to the dollars you are genuinely willing to lose here.
#
# HONEST SLEEVE (2026-07-01 decision): the owner's ~$14k of genuine options
# risk capital = cash + active swing-trade capital. The $50k invested portfolio
# and up to $40k of Schwab margin are DELIBERATELY EXCLUDED: the portfolio must
# not sit behind option trades, and borrowed margin is not "willing-to-lose"
# money. An earlier "$58k sleeve so a $5-wide spread fits" idea was rejected as
# reverse-engineering the sleeve to fit the trade -- the exact mistake this file
# and analysis/feasibility.py warn against.
RISK_SLEEVE          = 14_000    # $ genuinely willing to lose (cash + swing;
                                 # re-confirmed by the owner 2026-07-02)
# PER-TRADE RISK (owner decision 2026-07-02): a HARD DOLLAR CAP replaces the
# old "1% of sleeve" rule. $600 =~ 4.3% of the sleeve -- and under the assumed
# credits it is what makes the strategy TRADABLE at all: the 1% rule ($140)
# sat below the $2-wide ECONOMIC max loss ($142.60), i.e. zero contracts.
# The cap is PER TRADE, not per cluster: len(UNIVERSE) concurrent positions
# put ~$5,400 (~38.6% of the sleeve) at SIMULTANEOUS risk in the current
# 9-symbol universe. These names are emphatically not 9 independent bets --
# analysis/feasibility.py prints the portfolio view. Never raise this cap to
# make a width "fit"; that is reverse-engineering risk to fit the trade, the
# exact mistake this file warns against.
MAX_LOSS_PER_TRADE   = 600       # $ hard cap on economic max loss per trade
STARTING_CAPITAL     = 25_000    # account equity used by the backtest engine
                                 # (engine buying power; decoupled from the
                                 # risk sleeve above -- a few defined-risk
                                 # spreads need trivial buying power)

# ---------------------------------------------------------------------------
# UNIVERSE & WINDOW
# ---------------------------------------------------------------------------
# CONCENTRATION FLAG: SPY and QQQ overlap heavily with AAPL/MSFT/NVDA/AMZN,
# and PLTR/NOW/VST add high-beta thematic exposure rather than clean
# diversification. This universe is much closer to one growth/AI/power-risk
# cluster than 9 independent bets. In a risk-off or tech/AI drawdown, short-put
# spreads across these symbols can lose together. Treat "diversification" here
# with suspicion.
UNIVERSE             = [
    "SPY", "QQQ", "MSFT", "AAPL", "NVDA",
    "VST", "PLTR", "AMZN", "NOW",
]
BACKTEST_START       = "2018-01-01"   # must span 2018 / 2020 / 2022 regimes
# OOS WINDOW EXTENSION (2026-07-02, decided BLIND at pre-registration -- before
# any paid or post-IN_SAMPLE_END market data was fetched or opened): end moved
# 2024-12-31 -> 2026-06-30. Rationale: analysis/power_check.py measured the
# 2-year OOS window as underpowered at plausible edge sizes with an inflated
# false-PASS rate; +75% OOS weeks is the only free lever that improves both.
# The holdout stays untouched until the budgeted reveal. Registration freezes
# this via data_window_hash -- changing it AFTER registering = a NEW hypothesis.
BACKTEST_END         = "2026-06-30"
IN_SAMPLE_END        = "2022-12-31"   # in-sample <= this; out-of-sample after

# ---------------------------------------------------------------------------
# DATA & COSTS
# ---------------------------------------------------------------------------
DATA_PROVIDER        = "thetadata"    # swappable: select the Lumibot datasource
COMMISSION_PER_CONTRACT = 0.65        # per contract, per leg, each way
SLIPPAGE_HAIRCUT     = 0.01           # extra adverse fraction applied beyond mid
HALF_SPREAD_COST     = True           # assume crossing half the bid-ask per leg

# ---------------------------------------------------------------------------
# LIQUIDITY FILTERS (apply to BOTH legs before trading)
# ---------------------------------------------------------------------------
MIN_OPEN_INTEREST    = 100
MAX_SPREAD_PCT       = 0.10           # skip contracts wider than 10% bid-ask

# ---------------------------------------------------------------------------
# SHARED STRATEGY HORIZON
# ---------------------------------------------------------------------------
DTE_MIN              = 10             # never 0DTE

# ---------------------------------------------------------------------------
# STRATEGY A -- DEFINED-RISK PUT CREDIT SPREAD (volatility-risk-premium)
# ---------------------------------------------------------------------------
A_SHORT_PUT_DELTA    = 0.30          # sell the ~30-delta put (match on |delta|)
# Width under the $600 cap (2026-07-02; supersedes the old "$2-wide zero-slack
# threshold" note): ALL sweep widths now fit at assumed credits -- $1-wide
# (~$72.60 economic) 8 contracts, $2-wide (~$142.60) 4, $5-wide (~$352.60) 1.
# Feasibility no longer forces the width choice; the IN-SAMPLE width sweep
# decides it. $2-wide stays the registered candidate. Narrower widths remain
# the most commission/spread-punished per dollar of credit. Feasibility is
# NOT validation: the live data path must still skip trades whose actual
# conservative credit does not fit, and nothing here is real until measured
# quotes replace ASSUMED_CREDIT_FRAC in feasibility.py.
A_SPREAD_WIDTH       = 5             # buy the put this many $ lower
                                     # [WIDTH SWEEP ARM 2026-07-03: in-sample
                                     # only; restored to 2 after the arm run]
A_TARGET_DTE         = (30, 45)      # nearest expiration in band and >= DTE_MIN
A_PROFIT_TARGET      = 0.50          # close at 50% of entry credit captured
A_STOP_LOSS          = 2.0           # close if loss reaches 2x entry credit
A_CLOSE_AT_DTE       = 7             # always close by 7 DTE

# Width sweep: costs are ~fixed per contract but credit shrinks with width, so
# narrow spreads are far more cost-sensitive. Sweep WIDTH as the variable and
# keep MAX_LOSS_PER_TRADE fixed, rather than loosening risk to make trades "fit".
# INTEGRITY (2026-07-02): the sweep is judged IN-SAMPLE ONLY. Three widths
# against OOS_LOOK_BUDGET = 3 (a lifetime cap) would exhaust the entire OOS
# budget in one sweep; exactly ONE pre-registered width may ever reveal OOS.
A_SPREAD_WIDTH_SWEEP = [1, 2, 5]

# ---------------------------------------------------------------------------
# SCOREBOARD / VERDICT
# ---------------------------------------------------------------------------
# A verdict needs enough LOSSES, not enough trades -- a long win streak in a
# short-vol strategy is expected and proves nothing. Below this many losing
# trades, the harness returns INSUFFICIENT SAMPLE instead of pass/fail.
MIN_LOSSES_FOR_VERDICT = 10
BOOTSTRAP_SAMPLES      = 5_000        # for the expectancy confidence interval

# ---------------------------------------------------------------------------
# RESEARCH INTEGRITY (Phase 1A) -- frozen, verdict-affecting knobs
# ---------------------------------------------------------------------------
# These are hashed into the cost-model snapshot (research/hashing.py) and
# FROZEN before any out-of-sample reveal. Changing one starts a NEW
# pre-registered hypothesis; it must never be quietly retuned toward a PASS.
OOS_LOOK_BUDGET          = 3      # global cap on distinct hypotheses that may reveal OOS
BOOTSTRAP_BLOCK_EXPONENT = 1 / 3  # n^(1/3) blocking rate (Politis-White / Lahiri)
BOOTSTRAP_BLOCK_CONSTANTS = [0.5, 1, 2, 4]  # mean block = round(c * n_cohorts**exp)
COHORT_GRANULARITY       = "week"  # cross-sectional cohort key = ISO week of entry_date
FILL_MODEL_ID            = "conservative_bid_ask_plus_haircut_v1"  # bump if fill logic changes
