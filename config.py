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
# put ~$2,400 (~17.1% of the sleeve) at SIMULTANEOUS risk in the current
# 4-symbol universe. These names are emphatically not 4 independent bets --
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
# PROJECT SCOPE (owner decision 2026-07-03): the research universe is four
# names on one thesis -- nuclear/data-center power (VST, CEG) + Mag-7 cloud/AI
# (MSFT, AMZN). CONCENTRATION FLAG (unchanged in spirit): these four are one
# AI-infrastructure cluster, not four independent bets; in a risk-off or AI
# drawdown they can lose together. Treat "diversification" here with suspicion.
# Ordering note: smoke/demo paths use UNIVERSE[0]; CEG is listed LAST because
# its history is shortest (spun off 2022-02; chains cached 2022-02-09+).
# H1/H2/H3-era registered records carry their own frozen scope in the ledger
# and are unaffected by this edit.
UNIVERSE             = ["MSFT", "AMZN", "VST", "CEG"]
# Per-name study start dates ("eras") used by the descriptive studies
# (options_researcher/studies/*). AMZN starts POST-SPLIT: the close series is
# deliberately RAW (strike-aligned), so the 2022-06 20:1 split would read as a
# -95% cycle and corrupt cross-split P&L arithmetic; pre-split AMZN also had
# no usable fine strike grid (profiler finding). VST/CEG start 2023 (usable
# chain history); MSFT spans the full window.
STUDY_ERA_START      = {"MSFT": "2018-01-02", "AMZN": "2022-07-01",
                        "VST": "2023-01-01", "CEG": "2023-01-01"}
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
A_SPREAD_WIDTH       = 2             # buy the put this many $ lower
A_TARGET_DTE         = (30, 45)      # nearest expiration in band and >= DTE_MIN

# Attractiveness expiration ladder: (target_dte, lo, hi) per bucket. Per-bucket
# accept windows (NOT a flat tolerance) so the 2-week bucket can't pull in a
# ~4 DTE option. Windows are disjoint; the upper tolerance widens with tenor
# because monthlies thin to ~30-day spacing far out. Owner-frozen 2026-07-09.
A_LADDER_BUCKETS     = ((14, 10, 21), (30, 24, 38), (60, 50, 75),
                        (90, 76, 105), (120, 106, 140))

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

# ---------------------------------------------------------------------------
# H4/H5 RISK BUCKETS (owner decisions 2026-07-04; H5 scanner-first correction
# 2026-07-06). These caps constrain candidates and any tracked positions.
# THESIS: LEAPS calls, premium-capped (equity-replacement accounting).
# TACTICAL: short-dated long calls under the existing $600 economic cap.
# CSP: exactly one cash-secured put; collateral lives on the EQUITY side.
# ---------------------------------------------------------------------------
H4_THESIS_MAX_PREMIUM_PER_NAME = 10_000  # $ per underlying (owner amendment
                                         # 2026-07-04: 4k -> 10k; every 0.70d
                                         # ~1y LEAPS priced above the blind 4k
                                         # estimate; TOTAL below unchanged, so
                                         # effectively ONE full-size LEAPS)
H4_THESIS_MAX_PREMIUM_TOTAL    = 16_000  # $ across all LEAPS (owner amendment
                                         # 2026-07-06: 10k -> 16k; scanner
                                         # budget room for up to two full-size
                                         # LEAPS if later selected. No LEAPS
                                         # are currently open. Sizing cap, NOT
                                         # an edge parameter; noted in
                                         # ledger/facts.log, which is advisory
                                         # and un-chained -- see ledger/README)
H4_THESIS_MAX_POSITIONS        = 2
H4_THESIS_NAMES                = ["MSFT", "VST", "CEG"]
H4_THESIS_DELTA                = 0.70
H4_THESIS_DTE_BAND             = (270, 500)
H4_THESIS_ROLL_DTE             = 90      # roll LEAPS at or below this DTE
H4_TACTICAL_MAX_OPEN           = 2       # $600 per-trade cap unchanged
H4_TACTICAL_DELTA              = 0.40
H4_CSP_MAX_POSITIONS           = 1
H4_CSP_NAMES                   = ["VST", "AMZN"]
H4_CSP_DELTA                   = 0.20

# ---------------------------------------------------------------------------
# H5 ATTRACTIVENESS THRESHOLDS (frozen; owner-amendment only). Anchors:
# put-yield GREEN 1.0%/mo = Study E measured VST 0.20d average; CC-yield
# GREEN 0.8%/mo = Study C AMZN 0.20d collected while beating buy-and-hold;
# cushion = %OTM / (rv21/sqrt(12)); IV-rank grades flip sign buyer vs seller
# (Study A: high rank = paid more AND real risk higher -- never "free").
# ---------------------------------------------------------------------------
H5_PUT_YIELD_GREEN = 0.010
H5_PUT_YIELD_AMBER = 0.006
H5_CUSHION_GREEN   = 0.8
H5_CUSHION_AMBER   = 0.5
H5_CC_YIELD_GREEN  = 0.008
H5_CC_YIELD_AMBER  = 0.004
H5_CC_UPSIDE_GREEN = 0.03
H5_IVR_SELL_GREEN  = 0.5
H5_IVR_BUY_GREEN   = 0.3
H5_IVR_BUY_RED     = 0.7
# Seller VRP-PROXY gate: GREEN when front-month atm_iv (0.50d nearest monthly,
# 15-60 DTE, FORWARD-looking) >= rv21 (trailing 21-trading-day realized,
# BACKWARD-looking), i.e. iv_minus_rv >= 0. DESCRIPTIVE ONLY and a PROXY, not a
# true variance risk premium: it compares implied to TRAILING realized, not to
# realized over the option's own cycle, and the tenors only roughly match.
# Anchor is the SIGN of the proxy, not a tuned level. Separate badge from
# H5_IVR_SELL_GREEN (IV vs its own 1yr history).
H5_VRP_SELL_GREEN  = 0.0
H5_INCOME_DELTA    = 0.20     # CSP + CC short-leg target delta
H5_INCOME_DELTA_BAND = 0.15   # acceptance band around any target delta
                              # (single source: evaluator + studies import it)

# Portfolio flag: a short put is ASSIGNMENT_WATCH when the close sits within
# this fraction of the strike (descriptive flag only, never an action).
ASSIGNMENT_WATCH_PCT = 0.02

# H5 LEAPS entry trigger (owner-frozen 2026-07-07; ledger
# H5_ENTRY_TRIGGER_PREREG). ALL conditions must hold before the owner even
# evaluates an entry: close <= level AND iv_rank <= H5_ENTRY_IVR_MAX AND the
# 0.70-delta LEAPS candidate passes the liquidity gates. IVR_MAX is 0.5 (not
# the GREEN 0.3) because a pullback that hits the price level typically
# RAISES IV-rank; demanding bottom-tercile IV simultaneously risks a trigger
# that can never fire.
H5_ENTRY_TRIGGERS = {"VST": 140.0, "AMZN": 220.0}
H5_ENTRY_IVR_MAX = 0.5

# ---------------------------------------------------------------------------
# H7 -- swing options on volatile AI names (REGISTERED 2026-07-09, ledger
# trial_intent f1887c9d...; amendment e266770f... adds SMCI to the backtest
# set). Three lanes: H7a drawdown+stabilization long, H7b coil long, H7c
# rich-IV bull put spread. Values are FROZEN; changing any requires a logged
# hypothesis version (see .claude/skills/ledger-discipline). Spec:
# docs/superpowers/specs/2026-07-09-h7-swing-options-design.md (+v1.1).
# ---------------------------------------------------------------------------
H7_WATCHLIST = ["CRWV", "TEM", "PLTR", "NOW", "SMCI", "NVDA", "AMD", "AVGO"]
H7_CORE_LONG_ONLY = ["VST", "CEG", "MSFT", "AMZN"]  # H7a/b eligible; H7c stays H5's book
H7_EXCLUDED = ["HYLN"]                              # dead chain (~128 rows/day)

H7A_DRAWDOWN_MIN = 0.25         # drawdown from 52wk high to arm lane a
H7A_RECLAIM_LOOKBACK_D = 20     # stabilization = first close > prior 20d high
H7B_RANGE_MAX = 0.15            # (60d high - low)/spot coil ceiling
H7B_RANGE_LOOKBACK_D = 60
H7B_RV_PCTILE_MAX = 0.25        # 20d RV vs own 1yr history (min 6mo listed)
H7_RV_LOOKBACK_D = 21           # trailing realized vol (close-to-close, annualized)
H7_IV_CHEAP_K = 1.00            # IV <= RV*k -> single long call
H7_IV_PAR_K = 1.15              # cheap_k < IV <= par_k -> call debit spread
H7_IV_RICH_K = 1.25             # IV >= RV*k -> H7c short-premium branch

H7_LONG_DELTA_BAND = (0.55, 0.70)
H7_LONG_DTE_BAND = (60, 120)
H7_SPREAD_LONG_DELTA = 0.60
H7_SPREAD_SHORT_DELTA = 0.25
H7_LONG_TP_PCT = 1.00           # +100% take profit on long premium
H7_SPREAD_TP_FRAC_MAX = 0.75    # close debit spread at 75% of max value
H7_CLOSE_AT_DTE = 30            # time exit for the long lanes

H7C_SHORT_DELTA_MAX = 0.30
H7C_DTE_BAND = (30, 45)
H7C_CREDIT_FLOOR_FRAC = 0.30    # net credit >= 30% of width or no trade
H7C_WIDTH_FRAC_OF_SPOT = 0.10
H7C_TP_FRAC = 0.50              # buy back at 50% of credit
H7C_STOP_CREDIT_MULT = 2.0      # stop at 2x credit
H7C_MAX_CONCURRENT = 1          # one short-premium position basket-wide

H7_MONTHLY_AT_RISK = 6000       # owner-typed 2026-07-09; all lanes combined
H7_MAX_OPEN_PER_UNDERLYING = 1
H7_ADMIT_MIN_CONTRACTS = 5      # per-lane admission: >=5 NTM monthly contracts
H7_ADMIT_MAX_SPREAD_PCT = 0.05  # ...with spread <= 5% and OI >= MIN_OPEN_INTEREST
H7_EARNINGS_BAN_SESSIONS = 5    # no new entries within 5 sessions pre-report

H7_BACKTEST_SYMBOLS = ["NOW", "NVDA", "PLTR", "MSFT", "AMZN", "VST", "CEG", "SMCI"]
H7_BACKTEST_START = "2018-01-02"
H7_BACKTEST_END = "2026-06-30"

H7C_CLOSE_BEFORE_EARNINGS = True  # registered: short premium NEVER held
#                                   through a report; runner hard-closes by
#                                   the last session before any scheduled
#                                   report (review R13 pinned the constant)

# --- 7b-0 additions -------------------------------------------------------
# Owner-ratified gate decisions, ledger H7_AMENDMENT_V1_2 (f880b4d1...):
H7C_CLOSE_AT_DTE = 7             # v1.2(4): hard-close H7c at 7 DTE (mirrors H7_CLOSE_AT_DTE)
H7_DELTA_TOLERANCE = 0.07        # v1.2(7): +/-0.07 around EVERY registered delta target
#                                  (replaces the borrowed H5_INCOME_DELTA_BAND=0.15)
H7_LANE_PRIORITY = ("a", "b", "c")  # v1.2(1,2): same-day sleeve tie-break; a beats b on one name
H7C_TIEBREAK = "credit_to_width"    # v1.2(3): concurrent H7c candidates -> highest credit/width
# v1.2(5): H7C_STOP_CREDIT_MULT semantics = close when the EOD conservative
# buy-back mark >= 2x entry credit; realized exit recorded (H1/H2 semantics).
# v1.2(6): the pre-registered backtest is an ISOLATED-LANE DIAGNOSTIC --
# per-symbol/per-lane, portfolio caps NOT simulated; a different estimand
# from live. The forward paper window carries the portfolio-coupled test.

# Registered numbers previously hardcoded in the signal/watch layer (7b-0
# NO-GO remediation: every decision number lives on this freeze surface):
H7_IV_TENOR_DTE_BAND = (72, 108)  # registered IV measure: ATM ~90d, +/-18d
H7_NTM_BAND = 0.10               # admission NTM = strikes within +/-10% of raw spot
H7_DD_LOOKBACK_D = 252           # "52wk high" = trailing 252 sessions
H7B_RV_WINDOW_D = 20             # registered "20d RV"
H7B_RV_HISTORY_D = 252           # "...vs own 1yr history"
H7B_RV_MIN_HISTORY_D = 106       # "min 6mo listed": 126 sessions minus the RV window
# Owner-ratified 2026-07-10 (ledger H7_OWNER_DECISIONS_7B01): the earnings
# gate is CLEAR only when a point-in-time-valid assertion identifies the NEXT
# scheduled report, OR the company is PROVEN (a distinct occurred/verified
# realized-report record) to have reported within the previous grace window.
# Day grace+1 without a valid future assertion = EARNINGS-UNKNOWN (fails
# closed). Expired estimates / old scheduled dates NEVER start the grace.
H7_EARNINGS_POST_REPORT_GRACE_D = 45
H7_EARNINGS_ESTIMATE_CLUSTER_D = 14   # estimates within this many days refer
#                                       to the same report (frozen 7b-0.1;
#                                       was module-private in h7_earnings.py)
# 7b-2R finding 5 (owner review 2026-07-11): verdict-affecting numbers that
# had escaped into module constants move onto the freeze surface so any
# change invalidates config_hash and stales a committed diagnostic attempt.
H7_DIAGNOSTIC_CONTRACTS = 1      # per-position sizing of the isolated-lane
#                                  diagnostic (F3). NOTE: the decide-layer
#                                  sleeve math prices ONE contract; changing
#                                  this requires revisiting that math.
FEED_PUT_DELTA_BAND = (0.03, 0.65)   # offline-feed PUT inclusion band
FEED_CALL_DELTA_BAND = (0.10, 0.90)  # offline-feed CALL inclusion band
#   (plumbing, not tunables: strategies fail LOUD when a selected leg has no
#    feed Data -- a band miss can abort a run, never bias one. They still
#    gate which contracts CAN trade, hence frozen.)
H7_MAX_HOLD_BUFFER_D = 2         # chunk horizon = H7_LONG_DTE_BAND[1] + this
H7_WARMUP_EXTRA_SESSIONS = 2     # warm-up = DD lookback + reclaim lookback + this
H7_CLOSES_LOOKBACK_D = 600       # calendar-day closes preload before a chunk
# 7b-2R.2 (owner decision 2026-07-11): the ledger record hash of
# H7_AMENDMENT_V1_3, which permanently WITHDREW the 2018-2026 historical H7
# diagnostic as verdict-capable evidence. Once this record exists in a
# ledger, every historical-diagnostic entry point (attempt recording, OOS
# authorization, the gated runner tool) refuses BEFORE reading market data.
# A future conditional historical study requires a NEW hypothesis and a NEW
# registration; it may not reopen H7. Frozen here so config_hash binds it.
H7_HISTORICAL_WITHDRAWAL_HASH = (
    "6faa494538a87e3ff802815ac9301ec6c004963c118745df1ab66a69b9491e5c")

# ---------------------------------------------------------------------------
# Forward-roadmap Stage 1 (source health) -- OPERATIONAL alerting threshold,
# NOT a registered strategy parameter: it changes when a human is warned,
# never what the earnings gate returns or what any backtest/verdict does.
# LLM-proposed 2026-07-11 (one trading week of runway to refresh a schedule
# by hand before grace lapses into UNKNOWN); owner may retype.
H7_SOURCE_HEALTH_WARN_SESSIONS = 5
