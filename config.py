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
# YOUR money is the "options book" (the risk sleeve) and size 1% of THAT --
# not 1% of your whole net worth (which silently puts your stock portfolio
# behind every options trade) and not 1% of an arbitrary round number.
# Set RISK_SLEEVE to the dollars you are genuinely willing to lose here.
#
# HONEST SLEEVE (2026-07-01 decision): the owner's ~$14k of genuine options
# risk capital = cash + active swing-trade capital. The $50k invested portfolio
# and up to $40k of Schwab margin are DELIBERATELY EXCLUDED: the portfolio must
# not sit behind option trades, and borrowed margin is not "willing-to-lose"
# money. An earlier "$58k sleeve so a $5-wide spread fits" idea was rejected as
# reverse-engineering the sleeve to fit the trade -- the exact mistake this file
# and analysis/feasibility.py warn against.
RISK_SLEEVE          = 14_000    # $ genuinely willing to lose (cash + swing)
RISK_PER_TRADE       = 0.01      # max fraction of RISK_SLEEVE at risk per trade
STARTING_CAPITAL     = 25_000    # account equity used by the backtest engine
                                 # (engine buying power; decoupled from the
                                 # risk sleeve above -- 1-contract spreads need
                                 # trivial buying power)

# For the feasibility study we test sizing against several candidate sleeve
# sizes so you can SEE the trade-off rather than guess one. 14_000 is the
# owner's real sleeve; the others bracket it so the trade-off stays visible.
RISK_SLEEVE_CANDIDATES = [8_000, 14_000, 25_000, 58_000]

# ---------------------------------------------------------------------------
# UNIVERSE & WINDOW
# ---------------------------------------------------------------------------
# CONCENTRATION FLAG: SPY and QQQ overlap heavily with AAPL/MSFT/NVDA, which
# are top holdings of both. These five names are closer to ~1.5 independent
# bets than five -- effectively one tech-beta factor. In a tech drawdown every
# short-put spread loses together. Treat "diversification" here with suspicion.
UNIVERSE             = ["SPY", "QQQ", "MSFT", "AAPL", "NVDA"]
BACKTEST_START       = "2018-01-01"   # must span 2018 / 2020 / 2022 regimes
BACKTEST_END         = "2024-12-31"
IN_SAMPLE_END        = "2022-12-31"   # in-sample <= this; out-of-sample after

# ---------------------------------------------------------------------------
# DATA & COSTS
# ---------------------------------------------------------------------------
# Provider grades (verified live 2026-07-01, see data/<provider>.py headers):
#   "dolthub"      free, DEV/CROSS-CHECK ONLY -- thin chain subset, no open
#                  interest (liquidity filter fails closed), 2019-02+ coverage.
#   "alphavantage" candidate verdict-grade -- full chains w/ OI, 2008+, needs
#                  premium key (~$50/mo; free keys are gated and fail loud).
#   "thetadata"    Phase-0 stub until a subscription exists (OPRA-grade).
# Verdict-grade backtests must NOT run on "dolthub" data.
DATA_PROVIDER        = "dolthub"
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
# $2-wide is the CAPITAL-HONEST threshold candidate at the ~$14k sleeve -- NOT
# the "cost-efficient" width (narrower spreads are MORE commission/spread
# sensitive, not less). At 1% risk the per-trade budget is $140, which equals
# the $2-wide GROSS max loss exactly -- a ZERO-SLACK threshold (commissions and
# real-credit shortfalls are NOT in the feasibility formula, so true all-in risk
# can breach budget; the live data path must skip trades whose actual
# conservative credit does not fit). $5-wide does not fit this sleeve; $1-wide
# fits but is the most cost-punished. Not validated until real quotes replace
# ASSUMED_CREDIT_FRAC in feasibility.py.
A_SPREAD_WIDTH       = 2             # buy the put this many $ lower
A_TARGET_DTE         = (30, 45)      # nearest expiration in band and >= DTE_MIN
A_PROFIT_TARGET      = 0.50          # close at 50% of entry credit captured
A_STOP_LOSS          = 2.0           # close if loss reaches 2x entry credit
A_CLOSE_AT_DTE       = 7             # always close by 7 DTE

# Width sweep: costs are ~fixed per contract but credit shrinks with width, so
# narrow spreads are far more cost-sensitive. Sweep WIDTH as the variable and
# keep RISK_PER_TRADE fixed, rather than loosening risk to make trades "fit".
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
