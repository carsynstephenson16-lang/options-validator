"""7b-1 engine-level tests: H7LaneBacktest through the REAL Lumibot on
synthetic cached chains (loader patched; offline; no .cache/ dependency).

Covers the owner-required matrix: next-session entry causality, cancellation
on missing execution data, triggered vs scheduled exits, every exit reason,
simultaneous triggers, exactly-once cost accounting, year-boundary position
continuity, warm-up boundary, ~120-DTE horizon, final-window suppression,
adjusted-signal vs raw-spot separation, missing-leg loudness, pending-exit
retry, and call/put feed coexistence (asserted through both call and put
structures trading from one rights=("C","P") feed build).
"""

import unittest
from datetime import date, datetime, timezone
from unittest import mock

import pandas as pd

import config
from data import pandas_feed
from data.cache_runner import trading_days
from harness import run_h7_backtest as run_h7
from strategies.h7_backtest import H7LaneBacktest

SYM = "SYNH"
T_SIG = "2022-06-06"           # decision session (Monday)
EXPS = ("2022-07-15", "2022-08-19", "2022-09-16")   # monthlies: 39/74/102 DTE
SESSIONS = trading_days("2020-06-01", "2022-12-30")


def A(expected, status="confirmed", event="E1",
      known="2020-01-01T00:00:00+00:00"):
    ts = datetime.fromisoformat(known)
    return {"symbol": SYM, "event_id": f"{SYM}-{event}",
            "fiscal_period": "FYX", "expected_date": date.fromisoformat(expected),
            "session_timing": "amc", "status": status,
            "source_url": "https://example.test/ir",
            "known_as_of_utc": ts, "checked_at_utc": ts, "notes": ""}


FAR_REPORT = [A("2022-12-15")]   # covered and never banning inside fixtures


def chain_frame(center=70.0, iv=0.40, overrides=None, drop=None,
                exps=EXPS):
    """Calls: bid 14-1.5k falling with strike, delta 0.90-0.09k. Puts:
    bid 2.0+1.1k rising with strike, |delta| 0.10+0.09k. Executable lane-a
    long call (0.63 delta @ 102 DTE) and H7c bull put spread (short 0.28
    delta @ 39 DTE, credit >= 30% of the ~10%-of-spot width) both exist."""
    overrides = overrides or {}
    drop = drop or set()
    rows = []
    for k in range(10):
        strike = center - 10 + 2.5 * k
        for exp in exps:
            for right, bid, delta in (
                ("C", max(0.5, 14.0 - 1.5 * k), max(0.05, 0.90 - 0.09 * k)),
                ("P", 2.0 + 1.1 * k, -min(0.95, 0.10 + 0.09 * k)),
            ):
                if (exp, strike, right) in drop:
                    continue
                b, a = bid, round(bid * 1.04, 2)
                if (exp, strike, right) in overrides:
                    o = overrides[(exp, strike, right)]
                    b, a = o["bid"], o["ask"]
                rows.append({
                    "expiration": exp, "strike": strike, "right": right,
                    "bid": b, "ask": a, "open_interest": 900, "iv": iv,
                    "delta": delta, "gamma": 0.0, "theta": 0.0, "vega": 0.0,
                })
    return pd.DataFrame(rows)


def closes_pair(last_iso, post=(), pre_hi=130.0, pre_lo=62.0, reclaim=70.0,
                warm_sessions=None):
    """(adjusted, raw) close series over real sessions ending at `last_iso`
    plus len(post) sessions after it; the reclaim bar lands exactly on
    `last_iso`. raw == adjusted here (no-split fixture)."""
    upto = [s for s in SESSIONS if s <= last_iso]
    if warm_sessions is not None:
        upto = upto[-warm_sessions:]
    lo_n = 25
    vals = [pre_hi] * (len(upto) - lo_n - 1) + [pre_lo] * lo_n + [reclaim]
    after = [s for s in SESSIONS if s > last_iso][:len(post)]
    s = pd.Series(vals + list(post), index=upto + after, dtype=float)
    return s, s.copy()


def run_engine(lane, chains, closes_adj, closes_raw, assertions,
               start, end, cutoff=None):
    def fake_loader(symbol, start_iso, end_iso, *, allow_oos=False):
        return {d: c for d, c in chains.items() if start_iso <= d <= end_iso}

    with mock.patch.object(pandas_feed, "load_cached_chains", fake_loader):
        return run_h7._run_chunk(
            lane, SYM, start, cutoff or end, end, None,
            closes_adj=closes_adj, closes_raw=closes_raw,
            assertions=assertions, allow_oos=False)


def default_chains(first, last, overrides_by_day=None, drop_by_day=None,
                   iv=0.40, exps=EXPS):
    days = [s for s in SESSIONS if first <= s <= last]
    out = {}
    for d in days:
        out[d] = chain_frame(
            iv=iv, exps=exps,
            overrides=(overrides_by_day or {}).get(d),
            drop=(drop_by_day or {}).get(d),
        )
    return out


class NextSessionEntryAndCosts(unittest.TestCase):
    """Signal frozen at T; fill at exactly T+1's adverse pre-widened quote;
    costs (haircut once, commissions once) verified by hand math."""

    @classmethod
    def setUpClass(cls):
        # TP on 2022-06-08: call bid pumped so liquidation >= 2 x entry debit
        pump = {("2022-09-16", 67.5, "C"): {"bid": 25.00, "ask": 25.50}}
        chains = default_chains(
            "2022-06-02", "2022-06-13",
            overrides_by_day={"2022-06-08": pump, "2022-06-09": pump,
                              "2022-06-10": pump})
        adj, raw = closes_pair(T_SIG, post=[70.0] * 6)
        cls.trades, cls.cancelled = run_engine(
            "a", chains, adj, raw, FAR_REPORT, "2022-06-02", "2022-09-30")

    def test_exactly_one_trade_no_cancellations(self):
        self.assertEqual(len(self.trades), 1)
        self.assertEqual(self.cancelled, [])

    def test_signal_at_t_entry_at_t_plus_one(self):
        t = self.trades[0]
        self.assertEqual(t["signal_date"], "2022-06-06")
        self.assertEqual(t["entry_date"], "2022-06-07")

    def test_entry_fill_is_t_plus_one_adverse_quote(self):
        # ask 9.88 widened up 1% and ceiled to the cent -> 9.98; the trade's
        # capital_at_risk = debit*100 + one-leg round-trip commission
        t = self.trades[0]
        self.assertAlmostEqual(t["capital_at_risk"], 9.98 * 100 + 1.30, places=2)

    def test_exit_observed_then_executed_next_session(self):
        t = self.trades[0]
        self.assertEqual(t["exit_reason"], "profit_target")
        # fills confirm on 06-08 (F5), TP observed 06-08 or 06-09, executed
        # strictly one session after its observation
        self.assertIn(t["exit_decision_date"], ("2022-06-08", "2022-06-09"))
        expected_exec = {"2022-06-08": "2022-06-09",
                         "2022-06-09": "2022-06-10"}[t["exit_decision_date"]]
        self.assertEqual(t["exit_date"], expected_exec)

    def test_costs_exactly_once(self):
        # exit fill: bid 25.00 widened down 1% floored -> 24.75
        t = self.trades[0]
        self.assertAlmostEqual(
            t["pnl"], (24.75 - 9.98) * 100 - 1.30, places=2)

    def test_benchmark_columns_present(self):
        t = self.trades[0]
        self.assertAlmostEqual(t["underlying_entry_close"], 70.0)
        self.assertAlmostEqual(t["underlying_exit_close"], 70.0)


class MissingNextSessionCancels(unittest.TestCase):
    def test_entry_cancelled_never_chased(self):
        # no chain on 2022-06-07 (the execution session): entry cancels with
        # an explicit reason; no substitute session is tried
        chains = default_chains("2022-06-02", "2022-06-10")
        del chains["2022-06-07"]
        adj, raw = closes_pair(T_SIG, post=[70.0] * 4)
        trades, cancelled = run_engine(
            "a", chains, adj, raw, FAR_REPORT, "2022-06-02", "2022-09-30")
        self.assertEqual(trades, [])
        self.assertEqual(len(cancelled), 1)
        self.assertEqual(cancelled[0]["planned_execution"], "2022-06-07")
        self.assertIn(cancelled[0]["reason"],
                      ("execution_session_missing",
                       "no_chain_on_execution_session"))


class UnderlyingStopAndSimultaneous(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 2022-06-09: close breaks the episode low (62) AND the call bid is
        # pumped past the profit target -- both reasons must be retained and
        # the underlying stop must win the primary slot
        pump = {("2022-09-16", 67.5, "C"): {"bid": 25.00, "ask": 25.50}}
        chains = default_chains(
            "2022-06-02", "2022-06-14",
            overrides_by_day={"2022-06-09": pump, "2022-06-10": pump})
        adj, raw = closes_pair(T_SIG, post=[70.0, 70.0, 60.0, 60.0, 60.0])
        cls.trades, _ = run_engine(
            "a", chains, adj, raw, FAR_REPORT, "2022-06-02", "2022-09-30")

    def test_simultaneous_reasons_retained_priority_applied(self):
        self.assertEqual(len(self.trades), 1)
        t = self.trades[0]
        self.assertEqual(t["exit_decision_date"], "2022-06-09")
        self.assertEqual(t["exit_date"], "2022-06-10")
        self.assertEqual(t["exit_reason"], "underlying_stop")
        self.assertIn("profit_target", t["exit_reasons"])
        self.assertIn("underlying_stop", t["exit_reasons"])


class H7cScheduledDteExit(unittest.TestCase):
    """Bull put spread (puts trading from a calls+puts feed build) closed by
    H7C_CLOSE_AT_DTE ON the intended session, not one late."""

    @classmethod
    def setUpClass(cls):
        chains = default_chains("2022-06-02", "2022-07-11", iv=0.90)
        adj, raw = closes_pair(T_SIG, post=[70.0] * 30)
        cls.trades, cls.cancelled = run_engine(
            "c", chains, adj, raw, FAR_REPORT, "2022-06-02", "2022-09-30")

    def test_h7c_trade_and_exact_scheduled_session(self):
        self.assertEqual(len(self.trades), 1)
        t = self.trades[0]
        self.assertEqual(t["structure"], "bull_put_spread")
        self.assertEqual(t["entry_date"], "2022-06-07")
        # expiration 2022-07-15, H7C_CLOSE_AT_DTE=7 -> intended session is
        # 2022-07-08 (DTE exactly 7); one session late would be 2022-07-11
        self.assertEqual(t["exit_date"], "2022-07-08")
        self.assertEqual(t["exit_reason"], "scheduled_dte")


class H7cPreEarningsExit(unittest.TestCase):
    def test_hard_close_lands_last_session_before_report(self):
        assertions = [A("2022-06-24"), A("2022-12-15", event="E2")]
        chains = default_chains("2022-06-02", "2022-06-30", iv=0.90)
        adj, raw = closes_pair(T_SIG, post=[70.0] * 20)
        trades, _ = run_engine(
            "c", chains, adj, raw, assertions, "2022-06-02", "2022-09-30")
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual(t["exit_reason"], "pre_earnings")
        self.assertEqual(t["exit_date"], "2022-06-23")   # report 06-24


class H7cCreditStopExit(unittest.TestCase):
    def test_buyback_at_twice_credit_stops(self):
        crush = {("2022-07-15", 65.0, "P"): {"bid": 4.90, "ask": 5.00},
                 ("2022-07-15", 60.0, "P"): {"bid": 0.50, "ask": 0.60}}
        chains = default_chains(
            "2022-06-02", "2022-06-14", iv=0.90,
            overrides_by_day={"2022-06-09": crush, "2022-06-10": crush})
        adj, raw = closes_pair(T_SIG, post=[70.0] * 6)
        trades, _ = run_engine(
            "c", chains, adj, raw, FAR_REPORT, "2022-06-02", "2022-09-30")
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual(t["exit_reason"], "credit_stop")
        self.assertEqual(t["exit_date"], "2022-06-10")


class EarningsUnknownWhileOpen(unittest.TestCase):
    def test_f2_conservative_close_and_grace_boundary(self):
        # only coverage: an occurred report 2022-04-25. Day 45 (06-09) is
        # still CLEAR; day 46 (06-10) turns UNKNOWN while the H7c position is
        # open -> conservative close queued, executed 06-13.
        assertions = [A("2022-04-25", status="occurred")]
        chains = default_chains("2022-06-02", "2022-06-16", iv=0.90)
        adj, raw = closes_pair(T_SIG, post=[70.0] * 8)
        trades, _ = run_engine(
            "c", chains, adj, raw, assertions, "2022-06-02", "2022-09-30")
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual(t["exit_reason"], "earnings_unknown")
        self.assertEqual(t["exit_decision_date"], "2022-06-10")
        self.assertEqual(t["exit_date"], "2022-06-13")


class PendingExitRetry(unittest.TestCase):
    def test_missing_exit_quote_retries_first_valid_session(self):
        pump = {("2022-09-16", 67.5, "C"): {"bid": 25.00, "ask": 25.50}}
        # TP observed 06-08 -> exit queued for 06-09; the leg row is DROPPED
        # on 06-09 (no quote) -> pending exit retained; restored 06-10 ->
        # executes there
        chains = default_chains(
            "2022-06-02", "2022-06-14",
            overrides_by_day={"2022-06-08": pump, "2022-06-10": pump,
                              "2022-06-13": pump},
            drop_by_day={"2022-06-09": {("2022-09-16", 67.5, "C")}})
        adj, raw = closes_pair(T_SIG, post=[70.0] * 6)
        trades, _ = run_engine(
            "a", chains, adj, raw, FAR_REPORT, "2022-06-02", "2022-09-30")
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual(t["exit_reason"], "profit_target")
        self.assertEqual(t["exit_decision_date"], "2022-06-08")
        self.assertEqual(t["exit_date"], "2022-06-10")


class WarmupBoundary(unittest.TestCase):
    def test_no_signal_before_config_derived_history(self):
        chains = default_chains("2022-06-02", "2022-06-10")
        adj, raw = closes_pair(T_SIG, post=[70.0] * 4, warm_sessions=100)
        trades, cancelled = run_engine(
            "a", chains, adj, raw, FAR_REPORT, "2022-06-02", "2022-09-30")
        self.assertEqual(trades, [])
        self.assertEqual(cancelled, [])


class SplitDomainSeparation(unittest.TestCase):
    def test_adjusted_signals_raw_spot_strikes(self):
        # pre-split RAW closes are 10x the adjusted series; the chain quotes
        # post-split RAW strikes near 70. Signals (drawdown/reclaim/stop_ref)
        # must come from the ADJUSTED series while strike selection uses the
        # RAW spot -- mixing the domains would produce no trade at all here.
        pump = {("2022-09-16", 67.5, "C"): {"bid": 25.00, "ask": 25.50}}
        chains = default_chains(
            "2022-06-02", "2022-06-13",
            overrides_by_day={"2022-06-08": pump, "2022-06-09": pump,
                              "2022-06-10": pump})
        adj, _ = closes_pair(T_SIG, post=[70.0] * 6)
        raw = adj.copy()
        raw.loc[raw.index < T_SIG] = raw.loc[raw.index < T_SIG] * 10.0
        trades, cancelled = run_engine(
            "a", chains, adj, raw, FAR_REPORT, "2022-06-02", "2022-09-30")
        self.assertEqual(len(trades), 1)
        t = trades[0]
        # strike chosen in the RAW domain (near spot 70, not 700)
        self.assertEqual(t["structure"], "long_call")
        # benchmark column carries the ADJUSTED close
        self.assertAlmostEqual(t["underlying_entry_close"], 70.0)


class MissingLegFailsLoud(unittest.TestCase):
    def test_selected_leg_absent_from_feed_raises(self):
        strat = H7LaneBacktest.__new__(H7LaneBacktest)
        strat.lane = "a"
        strat.symbol = SYM
        strat._tradeable = frozenset()      # nothing tradeable
        strat._closes_adj = closes_pair(T_SIG)[0]
        strat._month_risk = {}
        action = {"kind": "long_call", "expiration": "2022-09-16",
                  "strike": 67.5, "delta": 0.63, "cost": 999.0,
                  "stop_ref": 62.0}
        with self.assertRaises(RuntimeError):
            strat._submit_entry(action, "2022-09-16", "2022-06-07",
                                "2022-06-06", 999.0, None)


class DteBandRevalidation(unittest.TestCase):
    def test_f1_out_of_band_at_execution_cancels(self):
        strat = H7LaneBacktest.__new__(H7LaneBacktest)
        strat.lane = "a"
        strat.symbol = SYM
        strat._chain_provider = lambda s, d: chain_frame()
        strat._assertions = FAR_REPORT
        strat._known_as_of_fn = (
            lambda iso: datetime(2022, 6, 8, tzinfo=timezone.utc))
        strat._month_risk = {}
        strat.cancelled_entries = []
        strat._tradeable = None
        # expiration only 59 DTE at the execution session: below the frozen
        # (60, 120) band -> cancel with the F1 reason
        strat._pending = {
            "action": {"kind": "long_call", "expiration": "2022-08-05",
                       "strike": 67.5, "delta": 0.63, "cost": 999.0,
                       "stop_ref": 62.0},
            "signal_date": "2022-06-06", "execute_iso": "2022-06-07"}
        strat._execute_pending_entry("2022-06-07")
        self.assertEqual(len(strat.cancelled_entries), 1)
        self.assertEqual(strat.cancelled_entries[0]["reason"],
                         "dte_out_of_band")


class YearBoundaryContinuity(unittest.TestCase):
    """A ~116-DTE position opened in December is neither duplicated, omitted,
    nor prematurely closed across the calendar-year chunk seam."""

    @classmethod
    def setUpClass(cls):
        t_sig = "2021-12-20"
        pump = {("2022-03-18", 67.5, "C"): {"bid": 25.00, "ask": 25.50},
                ("2022-04-15", 67.5, "C"): {"bid": 25.00, "ask": 25.50}}
        days = [s for s in SESSIONS if "2021-12-01" <= s <= "2022-02-10"]
        chains = {
            d: chain_frame(exps=("2022-03-18", "2022-04-15"),
                           overrides=pump if d >= "2022-01-18" else None)
            for d in days
        }
        upto = [s for s in SESSIONS if s <= t_sig]
        vals = ([130.0] * (len(upto) - 26) + [62.0] * 25 + [70.0])
        after = [s for s in SESSIONS if t_sig < s <= "2022-02-10"]
        adj = pd.Series(vals + [70.0] * len(after), index=upto + after,
                        dtype=float)
        cls.adj = adj

        def fake_loader(symbol, start_iso, end_iso, *, allow_oos=False):
            return {d: c for d, c in chains.items()
                    if start_iso <= d <= end_iso}

        with mock.patch.object(pandas_feed, "load_cached_chains", fake_loader), \
             mock.patch.object(run_h7, "_load_closes",
                               lambda sym, s, e, allow_oos: (adj, adj.copy())):
            out = run_h7.run_lane("a", start="2021-11-01", end="2022-06-30",
                                  symbols=[SYM], assertions=FAR_REPORT)
        cls.trades = out["trades"]
        cls.cancelled = out["cancelled"]

    def test_exactly_one_trade_across_the_seam(self):
        self.assertEqual(len(self.trades), 1)

    def test_entry_in_december_exit_in_january(self):
        t = self.trades[0]
        self.assertEqual(t["signal_date"], "2021-12-20")
        self.assertEqual(t["entry_date"], "2021-12-21")
        self.assertTrue(t["exit_date"].startswith("2022-01"))
        self.assertEqual(t["exit_reason"], "profit_target")


class FinalWindowSuppression(unittest.TestCase):
    def test_no_entry_when_horizon_exceeds_the_data_end(self):
        # window ends 50 days after the signal: the decision cutoff
        # (end - H7_MAX_HOLD_DAYS) falls before the signal day, so no
        # decision is made at all -- suppressed, not cancelled
        chains = default_chains("2022-06-02", "2022-07-26")
        adj, raw = closes_pair(T_SIG, post=[70.0] * 40)

        def fake_loader(symbol, start_iso, end_iso, *, allow_oos=False):
            return {d: c for d, c in chains.items()
                    if start_iso <= d <= end_iso}

        with mock.patch.object(pandas_feed, "load_cached_chains", fake_loader), \
             mock.patch.object(run_h7, "_load_closes",
                               lambda sym, s, e, allow_oos: (adj, raw)):
            out = run_h7.run_lane("a", start="2022-06-01", end="2022-07-26",
                                  symbols=[SYM], assertions=FAR_REPORT)
        self.assertEqual(out["trades"], [])
        self.assertEqual(out["cancelled"], [])


class ChunkMathTests(unittest.TestCase):
    def test_h7_max_hold_derived_from_frozen_config(self):
        self.assertEqual(run_h7.H7_MAX_HOLD_DAYS,
                         config.H7_LONG_DTE_BAND[1] + 2)

    def test_year_chunks_mirror_h1_semantics(self):
        chunks = run_h7._year_chunks(date(2018, 1, 2), date(2020, 12, 31))
        self.assertEqual(len(chunks), 3)
        sim_start, cutoff, sim_end = chunks[0]
        self.assertEqual(sim_start, "2018-01-02")
        self.assertEqual(cutoff, "2018-12-31")
        from datetime import timedelta
        self.assertEqual(
            sim_end, (date(2018, 12, 31)
                      + timedelta(days=run_h7.H7_MAX_HOLD_DAYS)).isoformat())


if __name__ == "__main__":
    unittest.main()
