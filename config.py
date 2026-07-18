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
# BLACK-SCHOLES DESCRIPTIVE DATA-QUALITY LAYER
# ---------------------------------------------------------------------------
# Frozen engineering conventions from the 2026-07-17 BS attractiveness spec
# sections 5/15. These identify gross data errors; they are not study
# thresholds and do not gate or size a trade.
BS_DELTA_EPS = 0.02          # dimensionless delta out-of-range tolerance
BS_NOARB_TOL = 0.02          # USD tolerance on American no-arbitrage bounds
BS_IV_EXTREME_LOW = 0.02     # decimal IV; values <= this are suspicious
BS_IV_EXTREME_HIGH = 5.0     # decimal IV; values >= this are suspicious

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
# VST 140->160 owner-directed 2026-07-15 (ledger H5_ENTRY_TRIGGER_AMENDMENT_V2):
# a DISCRETIONARY LOOSENING toward the market (close 158.43 already < 160, so
# the price leg is instantly satisfied); any entry graded under it is trigger
# v2, not the original 2026-07-07 pre-registration firing.
H5_ENTRY_TRIGGERS = {"VST": 160.0, "AMZN": 220.0}
H5_ENTRY_IVR_MAX = 0.5

# ---------------------------------------------------------------------------
# H6 -- post-earnings tactical long calls (REGISTERED 2026-07-08, ledger
# trial_intent 5d813b8f...).  Forward-paper only; no live-order path.  These
# values are a transcription of the chained registration, not a retune.
# ---------------------------------------------------------------------------
H6_NAMES = ("NVDA", "PLTR", "AMZN")
H6_EARNINGS_BAN_SESSIONS = 5
H6_POST_EARNINGS_SESSIONS = 5
H6_IVR_MAX = 0.70  # owner-typed 2026-07-14 (H6_TRIAL7_AMENDMENT_1; was 0.50;
                   # book/receipts empty at amendment -- forward-only; naked
                   # long calls at IVR 0.50-0.70 carry higher vega-crush risk,
                   # disclosed in the fact)
H6_DTE_BAND = (45, 90)
H6_DELTA_BAND = (0.30, 0.50)
H6_MAX_ASK_DOLLARS = 1_000
H6_MONTHLY_PREMIUM_AT_RISK = 2_000
H6_MAX_CONTRACTS_PER_NAME = 1
H6_MAX_CONCURRENT = 3
H6_TAKE_PROFIT_PCT = 1.00
H6_CLOSE_AT_DTE = 21
H6_MIN_COMPLETED_POSITIONS = 8
H6_HARD_KILL_FULL_LOSS_MONTHS = 3

# ---------------------------------------------------------------------------
# H8 -- pre-earnings tactical long calls (REGISTERED 2026-07-15, ledger
# trial_intent 1eed4ae6...). Forward-paper only; no live-order path. These
# values are a transcription of the chained registration, not a retune.
# All numbers LLM-decided under the owner's explicit written in-session
# delegation 2026-07-15 (disclosed in the registration). Design evidence:
# reports/2026-07-15-event-vol-descriptive-study.md (descriptive only).
# NVDA excluded: measured pre-event IV run-up ~0 across 36 events.
# ---------------------------------------------------------------------------
H8_NAMES = ("PLTR", "AMZN")
H8_DTE_BAND = (45, 90)
H8_DELTA_BAND = (0.30, 0.50)
H8_MAX_ASK_DOLLARS = 1_000
H8_ENTRY_WINDOW_SESSIONS = (15, 8)  # entries ONLY T-15..T-8 XNYS sessions
                                    # before a CONFIRMED report; estimated
                                    # dates = no entry (fail closed)
H8_IVR_MAX = 0.50                   # NaN IVR = no entry
H8_EXIT_SESSIONS_BEFORE_REPORT = 2  # hard close at T-2; date moving inside
                                    # T-2 forces close at next session close
H8_TAKE_PROFIT_PCT = 0.75
H8_CAP_SHARED_WITH_H6 = True        # combined H6+H8 premium at risk shares
                                    # H6_MONTHLY_PREMIUM_AT_RISK (USD 2k/mo);
                                    # never H8 and H6 open on the same
                                    # underlying simultaneously
H8_MAX_CONTRACTS_PER_NAME = 1
H8_MAX_CONCURRENT = 2
H8_MIN_COMPLETED_POSITIONS = 8
H8_HARD_KILL_FULL_LOSS_MONTHS = 3

# ---------------------------------------------------------------------------
# H7 -- swing options on volatile AI names (REGISTERED 2026-07-09, ledger
# trial_intent f1887c9d...; amendment e266770f... adds SMCI to the backtest
# set). Three lanes: H7a drawdown+stabilization long, H7b coil long, H7c
# rich-IV bull put spread. Values are FROZEN; changing any requires a logged
# hypothesis version (see .claude/skills/ledger-discipline). Spec:
# docs/superpowers/specs/2026-07-09-h7-swing-options-design.md (+v1.1).
# ---------------------------------------------------------------------------
H7_WATCHLIST = ["CRWV", "TEM", "PLTR", "NOW", "SMCI", "NVDA", "AMD", "AVGO",
                "IREN", "USAR", "ET"]  # IREN added H7_AMENDMENT_V1_5 2026-07-14;
                         # USAR added H7_AMENDMENT_V1_6 2026-07-15 (both
                         # owner-typed story names; ledger/facts.log). USAR =
                         # USA Rare Earth, rare-earth/magnet AI-supply-chain
                         # name; STAGED in H7_EXCLUDED until its base option-
                         # chain backfill completes.
H7_CORE_LONG_ONLY = ["VST", "CEG", "MSFT", "AMZN"]  # H7a/b eligible; H7c stays H5's book
H7_EXCLUDED = ["HYLN"]  # HYLN: dead chain (~128 rows/day). USAR ACTIVATED
# 2026-07-15 (owner-authorized): base chain cache 318 files spanning 2025-04-07
# ..2026-07-14 (USAR options first listed 2025-04-07; 566 pre-listing sessions
# are skip-and-logged CACHE_GAPs) + Yahoo closes/OHLCV; whole-universe
# h7_data_gate GO as-of 2026-07-14. See H7_AMENDMENT_V1_6 (+ADDENDUM),
# DATA_PULL_BACKFILL, DATA_PULL, USAR_ACTIVATION in ledger/facts.log. Data
# caveat: USAR closes begin 2023-07 = pre-merger SPAC (IPXX) history on the
# ticker; the flat pre-2025 SPAC series can distort H7b RV/coil math.
# IREN ACTIVATED
# 2026-07-15 (owner-authorized): base option-chain cache built, 1,054 files
# spanning 2022-04-29..2026-07-14 (IREN options first listed 2022-04-29; the
# 112 earlier days are pre-options-listing gaps, skip-and-logged). IREN now
# enters the H7 forward-watch universe (recent_topup/h7_data_gate/h7_watch/
# qm_watch). See facts H7_AMENDMENT_V1_5 + H7_AMENDMENT_V1_5_ADDENDUM +
# IREN_ACTIVATION + DATA_PULL_BACKFILL in ledger/facts.log.
# ET ADDED + ACTIVATED 2026-07-17 (H7_AMENDMENT_V1_8, owner-typed "register it
# anyway"; thesis = energy player in the AI buildout, owner-asserted, agent-
# labeled Inference not owner-verified). Base option-chain cache already
# complete (1,942 files 2018-10-22..2026-07-16; Jan-Oct 2018 pre-availability
# gaps skip-and-logged) + Yahoo closes/OHLCV (2,145 rows 2018-01-02..2026-07-16),
# so ET activates directly, not staged. TRADABILITY CAVEAT: ET (~$20 spot)
# FAILS the H7 liquidity gates -- 2026-07-16 nearest-monthly ATM spread ~10.5%
# > MAX_SPREAD_PCT 10% and 0 contracts pass the strict H7_ADMIT_MAX_SPREAD_PCT
# 5% gate -- so ET is watched but structurally cannot fire an entry
# (route=none), on top of the earnings entry-ban (no gating assertions yet,
# same posture as CRWV/IREN). ET is NOT in the frozen 2026-07-25 cutoff scope
# (H7_CUTOFF_SCOPE_FREEZE unchanged). See H7_AMENDMENT_V1_8 + ET_ACTIVATION in
# ledger/facts.log.

# Per-name entity floor for SIGNAL closes (ledger H7_AMENDMENT_V1_7,
# owner-delegated decision 2026-07-15): closes on a ticker that predate the
# current operating company (SPAC-shell prints) are a different economic
# entity and never feed trailing price signals (RV percentile, coil range,
# drawdown). Floor = first option-listing date, repo-verified from the chain
# cache -- a conservative post-merger anchor. Enforced in
# data.underlying_closes.load_closes_adjusted only; raw strike/spot/chain
# math is unaffected.
H7_SIGNAL_CLOSES_START = {"USAR": "2025-04-07"}  # pre-2025 = IPXX SPAC shell

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
H7_FORWARD_CONTRACTS = 1         # Stage 4 T+1 paper-lifecycle per-position size.
#                                  Owner-typed per ledger H7_STAGE4_SPEC_PREREG
#                                  (2026-07-13; spec sha256 f3f7ab31...). Stage 4
#                                  stays BUILD-ONLY / SYNTHETIC-ONLY / INACTIVE;
#                                  activation is a separate Stage 8 decision and
#                                  Stage 5 enforces H7_MONTHLY_AT_RISK.
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

# ---------------------------------------------------------------------------
# --- QM SIGNAL RESEARCH (Breakout / Parabolic descriptive signals) ---
# Spec: docs/superpowers/specs/2026-07-14-qm-signal-research-design.md
# (commit 5bf97f2). Scope: signals + read-only daily watch + one-shot event
# study ONLY -- no hypothesis, no book, no verdict, no live-order path.
# Owner gate PASSED 2026-07-14: every value below was typed by the owner in
# the 2026-07-14 session message and entered at owner direction (fact
# QM_STUDY_PREREG 2026-07-14 records the full set + decision rules).
# Frozen: no edit without a logged QM_STUDY_PREREG_V2, and never after
# viewing returns. qm_signals, qm_study and qm_watch still refuse to run if
# any value reverts to None or either QM fact is absent from ledger/facts.log.
QM_RUN_LOOKBACK = 60      # "30-100% move in ~1-3 months" ~= 60 sessions
QM_RUN_MIN_PCT = 0.30     # lower bound of the described prior run
QM_BASE_MIN_DAYS = 10     # "2 wk-2 mo consolidation" lower edge
QM_BASE_MAX_DAYS = 40     # upper edge
QM_BASE_MAX_DEPTH = 0.20  # tighter alternate: partial proxy for the missing
#                           higher-lows/tightening tests (disclosed superset)
QM_BASE_SMA = 20          # base-length-appropriate line (he surfs the 10 and 20)
QM_VOL_DRYUP_RATIO = 0.65  # "volume drying up during the base" (unanchored in source)
QM_PARA_LOOKBACK = 20     # large-cap window is "days to weeks" -- faster than 40
QM_PARA_MIN_PCT = 0.50    # his stated LARGE-CAP magnitude floor
QM_PARA_GREEN_DAYS = 3    # "3-5+ consecutive green days" lower edge
QM_PARA_EXT_PCT = 0.15    # stretched vs 20d SMA; 1.5x-SMA is small-cap scale and
#                           would be near-vacuous on mega caps. Counts-only fallback
#                           (pre-declared, needs QM_STUDY_PREREG_V2): 0.15 -> 0.10
QM_PARA_SMA = 20          # extension reference only (his MAs are the snapback target)
QM_HORIZONS = (5, 10, 20)  # pre-declared forward windows, frozen
QM_TRADABILITY_DTE = (30, 60)  # monthly-expiry DTE band for cards
QM_NTM_BAND = 0.10        # "near-ATM" = strikes within +/-10% of raw close
#                           (spec SS4/SS5 gap closed at build time; mirrors
#                           H7_NTM_BAND but frozen independently so QM never
#                           couples to H7's registered surface)

# ---------------------------------------------------------------------------
# --- ATTRACTIVENESS DASHBOARD v2 TECHNICALS (presentation layer ONLY) ---
# Spec: docs/superpowers/specs/2026-07-16-attractiveness-v2-technicals-
# context-design.md. LLM-asserted presentation-layer values (proposed
# 2026-07-16): window lengths for the dashboard's MA/breakout/momentum
# context strip. These are dashboard context only, NOT strategy gates --
# they gate nothing, size nothing, and the frozen H5/H6/H7 numbers above
# are untouched by anything in this block.
TECH_SMA_WINDOWS = (20, 50, 200)   # short/mid/long simple moving averages
TECH_BREAKOUT_LOOKBACK = 20        # prior-high window for breakout_20d
TECH_MOM_1M = 21                   # ~1 month of sessions for mom_1m
TECH_MOM_3M = 63                   # ~3 months of sessions for mom_3m
TECH_52W_LOOKBACK = 252            # ~52 weeks of sessions for high_52w

# LLM-asserted presentation-layer ordering weights — dashboard display only,
# NOT strategy gates; frozen H5/H6/H7 numbers untouched. They order the
# dashboard's Top-3 shortlist (select_top_picks) and nothing else: they gate
# nothing, size nothing, and never touch entry/exit logic.
PICK_GREEN_POINT = 1        # points per GREEN badge on a card
PICK_RANK_LEADER_BONUS = 2  # bonus when the card is its lane's rank leader
PICK_TECH_BONUS = 2         # bonus for technical confluence with the lane's direction

# Owner-pinned dashboard visibility (owner directive 2026-07-16: "for VST
# and AMZN I always want to see their picks"). Display only: each pinned
# symbol's best ADMISSIBLE card renders in its own strip, labeled
# "owner-pinned visibility — not ranked". Pinning never fabricates a card
# (an inadmissible symbol shows an honest gap) and never touches the Top-3.
PICK_PINNED_SYMBOLS = ["VST", "AMZN"]

# Earnings-calendar coverage horizon: a curated calendar whose last entry is
# older than this many days before an option's expiry cannot certify the
# cycle "clear of earnings" — the badge must read UNKNOWN, never GREEN.
# ~1 quarter (91d) + reporting slack. LLM-asserted, presentation layer.
EARNINGS_COVERAGE_DAYS = 98

# Attractiveness-dashboard display universe (presentation layer ONLY —
# owner-directed expansion 2026-07-16). DERIVED from the already-authorized
# H7 forward scope, never a new list of its own: adding a ticker here
# requires adding it to the H7 scope first (owner amendment). Must equal
# options_researcher.h7_scope.watch_universe() exactly — a unittest pins the
# equality. UNIVERSE above is untouched and still owns every backtest path.
ATTRACTIVENESS_UNIVERSE = [
    _s for _s in H7_WATCHLIST + H7_CORE_LONG_ONLY if _s not in H7_EXCLUDED
]

# ---------------------------------------------------------------------------
# --- LIVE MISSION-CONTROL DASHBOARD (presentation/plumbing layer ONLY) ---
# Spec: docs/superpowers/specs/2026-07-16-live-dashboard-design.md.
# LLM-asserted plumbing values (proposed 2026-07-16): throttling and
# staleness bounds for the on-demand live-preview server. These gate
# nothing, size nothing, and never touch entry/exit logic. The live lane
# is PREVIEW ONLY -- FIRE remains owned by entry_watch on completed-session
# closes (H5_ENTRY_TRIGGER_PREREG / amendment v2, unchanged).
LIVE_DASH_PORT = 8642              # 127.0.0.1 only; --port overrides
LIVE_POLL_SECONDS = 30             # browser polling interval
LIVE_CACHE_TTL_SECONDS = 25        # server-side payload cache TTL
LIVE_QUOTE_MAX_AGE_SECONDS = 120   # older quote timestamp => UNAVAILABLE
LIVE_PROBE_MAX_AGE_DAYS = 7        # recorded schema probe older => live lane off

# ---------------------------------------------------------------------------
# H9 -- post-earnings conditional HISTORICAL WRITTEN STUDY (spec
# docs/superpowers/specs/2026-07-16-h9-post-earnings-historical-study-DRAFT.md,
# owner-approved values 2026-07-16, entry mechanics disclosed in spec §5).
# One-run contract; kill-not-bless; NEVER a trading lane. Registration gated
# on the owner's external review (H9_REGISTERED fact required by the CLI gate).
# Construction is inherited from H6 (DTE/delta bands, TP, DTE-close); costs
# from the frozen repo cost model. Does NOT reopen the tombstoned H7
# historical diagnostic.
# ---------------------------------------------------------------------------
H9_NAMES = H7_BACKTEST_SYMBOLS          # the 8 audited archive names
H9_WINDOW = (H7_BACKTEST_START, H7_BACKTEST_END)
H9_REACTION_MIN = 0.02                  # owner-approved 2026-07-16
H9_NEXT_REPORT_EXIT_SESSIONS = 2        # owner-approved 2026-07-16
H9_MIN_ELIGIBLE_EVENTS = 60             # owner-approved 2026-07-16 (census floor)
H9_PREMIUM_CAP_DOLLARS = 600            # owner-approved: global MAX_LOSS_PER_TRADE binds
H9_SECONDARY_COHORT = ("NOW", "MSFT", "VST", "CEG")  # E1-uncontaminated, informational only
