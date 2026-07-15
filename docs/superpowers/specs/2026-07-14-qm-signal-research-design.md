# QM signal research — daily watch + event study (hybrid)

**Status: DESIGN APPROVED IN SESSION 2026-07-14 (hybrid path). Implementation
gated on the §7 pre-registration procedure — owner types every QM_* value
into `config.py` herself; all numbers below are LLM-asserted proposals.**

Owner scope override 2026-07-14 (to be logged as `QM_SCOPE_OVERRIDE` per §7):
this build predates the first H5/H6/H7 verdict, mirroring the H7 override of
2026-07-09. Parking-lot entry: `ideas-parking-lot.md` "Qullamaggie momentum
swing strategy" (commit `4367324`) — this spec is its authorized salvageable
core, not the full parked strategy.

## 1. What this is / is not

**Is:** a mechanical port of the two EOD-computable Qullamaggie setups
(momentum-continuation Breakout; Parabolic overextension) over the existing
12-name universe, wired to BOTH (a) a read-only daily watch that prints
option candidate cards when a signal fires, and (b) a pre-registered event
study measuring whether fires precede moves at all.

**Is not:** a hypothesis with a book or verdict (registration as "H8" happens
only if the event study earns it, as a separate future arc); an execution
model (no stops/trails/R-multiples — those are the parked strategy's trading
layer); the Episodic Pivot setup (intraday opening-range entry — unbuildable
on EOD data, stays parked); a shorting vehicle (parabolic fires are signals;
any tradable expression stays long-premium/defined-risk per repo mandate);
TradingView anything (parked 2026-07-13, boundary risk); a live-order path
(never).

## 2. Architecture (three units + one CLI)

1. **`data/underlying_ohlcv.py`** — daily OHLCV sibling of the closes store.
   Same free Yahoo v8 chart endpoint already trusted by
   `data/underlying_closes.py` (provider decision 2026-07-04), extracting
   open/high/low/close/volume instead of close-only. Split handling reuses
   the existing `SPLITS` registry semantics: prices un-split-adjusted to
   align with raw history the same way closes are, volume adjusted
   inversely; a `load_ohlcv_adjusted()` twin provides split-continuous
   series for signal math (MAs, ranges, volume baselines). Cache:
   `.cache/underlying_ohlcv/<SYMBOL>.parquet`, blind (never prints values),
   `allow_oos=True` call sites only (disclosed post-2022 look, same as
   profilers). No new dependency, no paid API.
2. **`options_researcher/qm_signals.py`** — pure functions
   `breakout_fire(df, t) -> bool` and `parabolic_fire(df, t) -> bool` using
   only rows dated ≤ t (trailing windows; no look-ahead by construction).
   Constants only from `config.py` QM_* block.
3. **`options_researcher/qm_study.py`** — the event study CLI (§5).
4. **`options_researcher/qm_watch.py`** — the daily card view (§4).

## 3. Signal definitions (mechanical, frozen at pre-registration)

All series are split-adjusted; all windows are trailing (data ≤ t only).

**Breakout (momentum continuation, long-side signal):** fire at session t iff
a base window B exists satisfying 1–3 and t triggers 4:
1. **Base search (deterministic):** B is the window of length L ending at
   session t−1, taking the largest L in
   [`QM_BASE_MIN_DAYS`, `QM_BASE_MAX_DAYS`] that satisfies (a) depth
   (max high − min low)/min low ≤ `QM_BASE_MAX_DEPTH`, and (b) every close
   in B ≥ that session's `QM_BASE_SMA`-day SMA (the "surfing the moving
   average" rule).
2. **Prior run:** over the `QM_RUN_LOOKBACK` sessions ending at B's first
   session, max close-to-close gain ≥ `QM_RUN_MIN_PCT`.
3. **Volume dry-up:** mean volume in B ≤ `QM_VOL_DRYUP_RATIO` × mean volume
   over the run window from rule 2.
4. **Trigger:** close at t > max high of B.

**Parabolic (overextension, fade signal — signal-only):** fire at t iff:
1. Gain over trailing `QM_PARA_LOOKBACK` sessions ≥ `QM_PARA_MIN_PCT`.
2. ≥ `QM_PARA_GREEN_DAYS` consecutive up-closes ending at t.
3. Close ≥ (1 + `QM_PARA_EXT_PCT`) × the `QM_PARA_SMA`-day SMA.

**Dedupe (both signals, study and watch):** a streak of consecutive
qualifying sessions counts once, at its first session. A name may refire
Breakout only when the newly detected base window starts strictly after the
prior fire's trigger session; Parabolic refires only after at least one
non-qualifying session.

## 4. Daily watch — `qm_watch` (the "look at the chart, then the prices" step)

Runs after the existing ritual (top-up → health → gate → h7/h6 watches), on
the same evaluation session. For each of the 12 names it evaluates both
signals on the OHLCV cache and prints one line per name; on a fire it prints
option candidate cards from that session's cached chain:

- **Breakout fire →** near-ATM long call and call debit spread candidates in
  the `QM_TRADABILITY_DTE` band: strikes, ask/bid, adverse-priced cost
  (`adverse_buy`/`adverse_sell`, the canonical transforms), breakeven,
  per-leg liquidity via `passes_liquidity()`. Presentation mirrors
  `attractiveness` cards.
- **Parabolic fire →** the signal line prints with long-put / put-debit-
  spread candidates, same pricing discipline, labeled FADE SIGNAL.
- Every fire block carries the banner: **"UNVALIDATED SIGNAL — descriptive
  screen; no forward evidence exists until the §5 study reports; not an
  entry recommendation; no book path."**

The watch never writes positions, receipts, facts, or files (stdout only),
and does not read or affect the H5/H6/H7 books. It fails closed per name on
missing/stale OHLCV or a missing chain file for the session (prints the gap,
no silent skip).

## 5. Event study — `qm_study`

Over the full cached OHLCV history per name (CEG from 2022 listing;
CRWV/TEM from their listings — thin history reads as thin, never padded):

- Per fire: forward adjusted-close returns at each horizon in `QM_HORIZONS`;
  max favorable / max adverse excursion (adjusted high / adjusted low vs the
  fire session's adjusted close) over the longest horizon; option tradability that session (a chain file exists AND
  ≥1 near-ATM contract in `QM_TRADABILITY_DTE` passes `passes_liquidity()`;
  no chain cached → counted "no chain", excluded from the tradability rate's
  denominator, disclosed).
- Parabolic outcomes additionally reported sign-flipped (the fade view),
  labeled as such.
- **Baseline:** identical metrics over every session of the same name/period
  (the unconditional distribution). Every fire statistic is presented next
  to its baseline; no baseline, no claim.
- Output: `reports/YYYY-MM-DD-qm-base-rates.md` — counts, per-name × setup
  tables, tradability rates, caveats block up top (12 large-cap AI names ≠
  Qullamaggie's small-cap universe; EOD approximation; selection context of
  the 12 names). Vocabulary discipline applies: no "works/edge/confirmed";
  only "fired N times / outcomes vs baseline / consistent with".

## 6. Config block — `QM_*` (LLM-asserted proposals; OWNER TYPES the values)

| Constant | Proposed | Basis (all Inference from the strategy description) |
|---|---|---|
| `QM_RUN_LOOKBACK` | 60 | "30–100% move in ~3 months" ≈ 60 sessions |
| `QM_RUN_MIN_PCT` | 0.30 | lower bound of the described prior run |
| `QM_BASE_MIN_DAYS` / `QM_BASE_MAX_DAYS` | 10 / 40 | "2–8 week consolidation" |
| `QM_BASE_MAX_DEPTH` | 0.25 | "tight" base ceiling |
| `QM_BASE_SMA` | 20 | "surfing the 10-day or 20-day SMA" — one knob; owner may type 10 for the tighter line |
| `QM_VOL_DRYUP_RATIO` | 0.65 | "volume drying up during the base" |
| `QM_PARA_LOOKBACK` | 40 | "100%+ in a short time" ≈ 2 months |
| `QM_PARA_MIN_PCT` | 1.00 | the 100% threshold |
| `QM_PARA_GREEN_DAYS` | 3 | "3–5+ consecutive green days" (lower edge) |
| `QM_PARA_EXT_PCT` / `QM_PARA_SMA` | 0.50 / 20 | "extreme vertical" vs 20-day |
| `QM_HORIZONS` | (5, 10, 20) | pre-declared forward windows |
| `QM_TRADABILITY_DTE` | (30, 60) | monthly-expiry band the repo targets |

## 7. Pre-registration procedure (before any study run or watch output)

1. Owner reads this spec; accepts/adjusts each §6 value and **types them into
   `config.py`** (implementation arc is test-first and may scaffold the block
   with placeholders that fail loudly until owner values land).
2. Append `QM_SCOPE_OVERRIDE 2026-07-14` fact: owner overrode the
   verdict-first standing rule for this signal-research build (chat decision
   2026-07-13/14), scope = signals + watch + event study only, no
   hypothesis/book/verdict.
3. Append `QM_STUDY_PREREG` fact: spec sha256 at the signed-off commit, the
   owner-typed values, horizons frozen, one-run-then-report contract (the
   study runs once per data vintage; re-runs on new data are new dated
   reports, never threshold retunes without a new fact).
4. Only then the implementation arc opens on its own branch
   (`feature/qm-signal-research` off current `main`), independent review
   before merge.

## 8. Testing (unittest, offline, synthetic frames)

- Breakout: fires on a hand-built run→tight-base→new-high fixture; refuses
  when depth too wide, volume not drying, no prior run, close below SMA, or
  no new high; fires once per base.
- Parabolic: fires on the constructed vertical; refuses at N−1 green days /
  insufficient extension.
- No-look-ahead property: truncating the frame after t never changes the
  signal at t (both signals).
- Study math: forward returns / MFE / MAE / baseline against hand-computed
  fixtures; "no chain" exclusion accounting.
- OHLCV layer: Yahoo payload → frame parse from a mocked payload (no
  network); split adjustment on O/H/L and inverse on volume; blindness
  (store/load never prints values).
- Watch: fire → cards rendered with adverse pricing + liquidity flags from a
  fixture chain; per-name fail-closed on missing OHLCV/chain; stdout-only
  (no file writes).

## 9. Out of scope

Episodic Pivot (intraday), ADR stops / MA trails / R-multiple exits (trading
layer of the parked strategy), any short-selling execution, universe
expansion beyond the 12 names, TradingView integration, threshold
optimization/sweeps, any book/receipt/verdict machinery, any live-order path
(never).
